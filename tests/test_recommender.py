import unittest
from types import SimpleNamespace
from unittest.mock import patch

from wajhati.services import recommender
from wajhati.services.recommender import generate_itinerary, match_destinations


class MatchDestinationsTests(unittest.TestCase):
    def test_match_destinations_only_returns_requested_city(self):
        destinations = [
            SimpleNamespace(
                name="Riyadh Museum",
                city="Riyadh",
                estimated_cost=120.0,
                category="cultural",
                description="A cultural museum in Riyadh",
            ),
            SimpleNamespace(
                name="Jeddah Beach",
                city="Jeddah",
                estimated_cost=80.0,
                category="leisure",
                description="A relaxing seaside destination",
            ),
        ]

        matched = match_destinations(
            destinations,
            city="Riyadh",
            budget=500.0,
            interests=["cultural", "leisure"],
        )

        self.assertEqual([destination.name for destination in matched], ["Riyadh Museum"])

    def test_match_destinations_returns_empty_list_when_city_has_no_matches(self):
        destinations = [
            SimpleNamespace(
                name="Abha Adventure",
                city="Abha",
                estimated_cost=180.0,
                category="adventure",
                description="Mountain trails and outdoor activities",
            )
        ]

        matched = match_destinations(
            destinations,
            city="Riyadh",
            budget=500.0,
            interests=["adventure"],
        )

        self.assertEqual(matched, [])

    def test_match_destinations_falls_back_to_any_destination_in_selected_city(self):
        destinations = [
            SimpleNamespace(
                name="Riyadh Luxury",
                city="Riyadh",
                estimated_cost=900.0,
                category="luxury",
                description="High-end experience",
            ),
            SimpleNamespace(
                name="Riyadh Walk",
                city="Riyadh",
                estimated_cost=50.0,
                category="leisure",
                description="Easy city walk",
            ),
        ]

        matched = match_destinations(
            destinations,
            city="Riyadh",
            budget=100.0,
            interests=["wildlife"],
        )

        self.assertEqual([destination.name for destination in matched], ["Riyadh Walk", "Riyadh Luxury"])

    def test_match_destinations_without_city_uses_all_destinations(self):
        destinations = [
            SimpleNamespace(
                name="Riyadh Walk",
                city="Riyadh",
                estimated_cost=50.0,
                category="leisure",
                description="Easy city walk",
            ),
            SimpleNamespace(
                name="Jeddah Corniche",
                city="Jeddah",
                estimated_cost=80.0,
                category="leisure",
                description="Waterfront and family activities",
            ),
        ]

        matched = match_destinations(
            destinations,
            city="",
            budget=100.0,
            interests=["leisure"],
        )

        self.assertEqual(len(matched), 2)


class GenerateItineraryTests(unittest.TestCase):
    def test_generate_itinerary_falls_back_to_rule_based_when_ai_disabled(self):
        destinations = [
            SimpleNamespace(
                name="Riyadh Museum",
                city="Riyadh",
                estimated_cost=120.0,
                category="cultural",
                description="A cultural museum in Riyadh",
            )
        ]

        generated = generate_itinerary(
            destinations,
            duration_days=1,
            budget=500.0,
            trip_type="cultural",
            interests=["cultural"],
            ai_settings={
                "enabled": False,
                "provider": "gemini",
                "model": "gemini-2.5-flash",
                "api_key": "",
                "system_prompt": "Return JSON",
            },
        )

        self.assertEqual(len(generated["items"]), 1)
        self.assertEqual(generated["items"][0]["title"], "Riyadh Museum")

    def test_generate_itinerary_uses_ai_when_enabled_and_available(self):
        destinations = [
            SimpleNamespace(
                name="Riyadh Museum",
                city="Riyadh",
                estimated_cost=120.0,
                category="cultural",
                description="A cultural museum in Riyadh",
            )
        ]

        with patch.object(
            recommender,
            "_generate_itinerary_with_gemini",
            return_value={"items": [{"day_number": 1, "title": "AI Plan", "notes": "test", "estimated_cost": 99.0}], "estimated_total_cost": 99.0},
        ) as mocked_gemini:
            generated = generate_itinerary(
                destinations,
                duration_days=1,
                budget=500.0,
                trip_type="cultural",
                interests=["cultural"],
                ai_settings={
                    "enabled": True,
                    "provider": "gemini",
                    "model": "gemini-2.5-flash",
                    "api_key": "secret",
                    "system_prompt": "Return JSON",
                },
            )

        self.assertTrue(mocked_gemini.called)
        self.assertEqual(generated["items"][0]["title"], "AI Plan")
