import unittest

from wajhati import create_app, db
from wajhati.models import Destination


class TestConfig:
    SECRET_KEY = "test-secret"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TESTING = True


class ItineraryApiTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()

        with self.app.app_context():
            db.drop_all()
            db.create_all()
            db.session.add_all(
                [
                    Destination(
                        name="Diriyah",
                        city="Riyadh",
                        category="cultural",
                        description="Historic cultural district in Riyadh",
                        estimated_cost=150.0,
                    ),
                    Destination(
                        name="Jeddah Corniche",
                        city="Jeddah",
                        category="leisure",
                        description="Waterfront destination with family activities",
                        estimated_cost=90.0,
                    ),
                ]
            )
            db.session.commit()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_generate_itinerary_only_includes_requested_city(self):
        response = self.client.post(
            "/api/itineraries/generate",
            json={
                "destination_city": "Riyadh",
                "duration_days": 2,
                "budget": 1000,
                "trip_type": "family",
                "interests": ["cultural", "leisure"],
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["items"])
        self.assertEqual({item["title"] for item in payload["items"]}, {"Diriyah"})

    def test_generate_itinerary_returns_404_when_city_has_no_matches(self):
        response = self.client.post(
            "/api/itineraries/generate",
            json={
                "destination_city": "Madinah",
                "duration_days": 2,
                "budget": 1000,
                "trip_type": "family",
                "interests": ["cultural"],
            },
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.get_json()["error"],
            "No destinations matched the selected preferences",
        )
