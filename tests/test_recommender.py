import unittest
from types import SimpleNamespace

from wajhati.services.recommender import match_destinations


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
