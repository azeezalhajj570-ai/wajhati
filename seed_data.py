from wajhati import create_app, db
from wajhati.models import Destination

app = create_app()

sample_destinations = [
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

with app.app_context():
    db.create_all()
    existing = {d.name for d in Destination.query.all()}
    created = 0
    for item in sample_destinations:
        if item["name"] in existing:
            continue
        db.session.add(Destination(**item))
        created += 1
    db.session.commit()
    print(f"Seed completed. Added {created} destinations.")
