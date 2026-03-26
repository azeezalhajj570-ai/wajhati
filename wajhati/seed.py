from wajhati import db
from wajhati.models import Destination


SAMPLE_DESTINATIONS = [
    {
        "name": "Historic Diriyah",
        "city": "Riyadh",
        "category": "cultural",
        "description": "UNESCO heritage district with museums and traditional Najdi architecture.",
        "estimated_cost": 120,
        "latitude": 24.7376,
        "longitude": 46.5718,
        "season": "winter",
    },
    {
        "name": "Kingdom Centre Sky Bridge",
        "city": "Riyadh",
        "category": "leisure",
        "description": "Modern landmark with panoramic city views and shopping options.",
        "estimated_cost": 80,
        "latitude": 24.7116,
        "longitude": 46.6742,
        "season": "all",
    },
    {
        "name": "AlUla Old Town",
        "city": "AlUla",
        "category": "cultural",
        "description": "Ancient settlement and heritage attractions surrounded by stunning landscapes.",
        "estimated_cost": 250,
        "latitude": 26.6084,
        "longitude": 37.9232,
        "season": "winter",
    },
    {
        "name": "Edge of the World",
        "city": "Riyadh",
        "category": "adventure",
        "description": "A dramatic cliff formation for hiking and desert exploration.",
        "estimated_cost": 150,
        "latitude": 24.9472,
        "longitude": 45.6073,
        "season": "winter",
    },
    {
        "name": "Jeddah Corniche",
        "city": "Jeddah",
        "category": "leisure",
        "description": "Waterfront attractions, cafes, and family-friendly walking areas.",
        "estimated_cost": 60,
        "latitude": 21.6073,
        "longitude": 39.1043,
        "season": "all",
    },
    {
        "name": "Farasan Islands",
        "city": "Jazan",
        "category": "nature",
        "description": "Island destination with beaches, marine life, and boat tours.",
        "estimated_cost": 300,
        "latitude": 16.7149,
        "longitude": 42.1188,
        "season": "spring",
    },
]


def seed_demo_destinations():
    existing_names = {
        name
        for (name,) in db.session.query(Destination.name)
        .filter(Destination.name.isnot(None))
        .all()
    }

    pending = [
        Destination(**item)
        for item in SAMPLE_DESTINATIONS
        if item["name"] not in existing_names
    ]
    if not pending:
        return 0

    db.session.add_all(pending)
    db.session.commit()
    return len(pending)
