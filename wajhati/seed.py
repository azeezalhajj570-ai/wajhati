from wajhati import db
from wajhati.models import Destination, User
from wajhati.translations import SAUDI_CITIES


DESTINATION_VARIANTS = {
    "cultural": [
        {
            "name_suffix": "Heritage Quarter",
            "description": "Historic district with local architecture, museums, and cultural storytelling experiences.",
            "estimated_cost": 90,
            "season": "winter",
        },
        {
            "name_suffix": "Traditional Market Walk",
            "description": "Lively market area with regional crafts, food stalls, and heritage shops.",
            "estimated_cost": 70,
            "season": "all",
        },
        {
            "name_suffix": "Cultural Village",
            "description": "Interactive heritage site featuring art, performances, and family-friendly exhibitions.",
            "estimated_cost": 110,
            "season": "spring",
        },
    ],
    "leisure": [
        {
            "name_suffix": "Corniche Promenade",
            "description": "Relaxed public promenade with cafes, photo spots, and evening walking areas.",
            "estimated_cost": 60,
            "season": "all",
        },
        {
            "name_suffix": "City View Lounge",
            "description": "Modern leisure destination with panoramic views, dining, and shopping nearby.",
            "estimated_cost": 95,
            "season": "all",
        },
        {
            "name_suffix": "Family Leisure Park",
            "description": "Open-air recreation area with gardens, seating zones, and activities for families.",
            "estimated_cost": 80,
            "season": "autumn",
        },
    ],
    "adventure": [
        {
            "name_suffix": "Desert Trail Camp",
            "description": "Outdoor adventure zone offering guided trails, scenic overlooks, and camp experiences.",
            "estimated_cost": 140,
            "season": "winter",
        },
        {
            "name_suffix": "Rock Ridge Escape",
            "description": "Rugged terrain destination popular for hiking, climbing, and exploration trips.",
            "estimated_cost": 180,
            "season": "spring",
        },
        {
            "name_suffix": "Adventure Valley Route",
            "description": "Exciting nature corridor with off-road access, viewpoints, and active group excursions.",
            "estimated_cost": 160,
            "season": "autumn",
        },
    ],
    "nature": [
        {
            "name_suffix": "Green Oasis Reserve",
            "description": "Peaceful natural setting with shaded paths, native plants, and quiet picnic areas.",
            "estimated_cost": 75,
            "season": "spring",
        },
        {
            "name_suffix": "Mountain View Garden",
            "description": "Scenic landscape area known for fresh air, open views, and relaxing nature walks.",
            "estimated_cost": 85,
            "season": "summer",
        },
        {
            "name_suffix": "Wildlife Nature Park",
            "description": "Protected outdoor area where visitors can enjoy local ecosystems and birdwatching.",
            "estimated_cost": 100,
            "season": "winter",
        },
    ],
}

DEFAULT_USERS = [
    {
        "name": "admin",
        "email": "admin@wajhati.local",
        "password": "admin",
        "is_admin": True,
    },
    {
        "name": "user",
        "email": "user@wajhati.local",
        "password": "user",
        "is_admin": False,
    },
]


def _generate_demo_destinations():
    generated = []
    for city in SAUDI_CITIES:
        for category, variants in DESTINATION_VARIANTS.items():
            for variant in variants:
                generated.append(
                    {
                        "name": f"{city} {variant['name_suffix']}",
                        "city": city,
                        "category": category,
                        "description": variant["description"],
                        "estimated_cost": variant["estimated_cost"],
                        "latitude": None,
                        "longitude": None,
                        "season": variant["season"],
                    }
                )
    return generated


def seed_demo_destinations():
    sample_destinations = _generate_demo_destinations()
    existing_names = {
        name
        for (name,) in db.session.query(Destination.name)
        .filter(Destination.name.isnot(None))
        .all()
    }

    pending = [
        Destination(**item)
        for item in sample_destinations
        if item["name"] not in existing_names
    ]
    if not pending:
        return 0

    db.session.add_all(pending)
    db.session.commit()
    return len(pending)


def seed_default_users():
    created = False

    for account in DEFAULT_USERS:
        user = User.query.filter_by(email=account["email"]).first()
        if user:
            if account["is_admin"] and not user.is_admin:
                user.is_admin = True
                created = True
            continue

        user = User(
            name=account["name"],
            email=account["email"],
            is_admin=account["is_admin"],
        )
        user.set_password(account["password"])
        db.session.add(user)
        created = True

    if created:
        db.session.commit()

    return int(created)
