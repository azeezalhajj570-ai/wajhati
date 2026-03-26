from wajhati import create_app
from wajhati.seed import seed_demo_destinations

app = create_app()

with app.app_context():
    created = seed_demo_destinations()
    print(f"Seed completed. Added {created} destinations.")
