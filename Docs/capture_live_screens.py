import sys
from pathlib import Path
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from wajhati import create_app, db
from wajhati.models import Itinerary, ItineraryItem, User

OUT_DIR = ROOT / "Docs" / "_generated_report" / "live_screens"
BASE_URL = "http://127.0.0.1:5000"


def shot(page, name):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"shot:{name}", flush=True)
    page.screenshot(path=str(OUT_DIR / f"{name}.png"), full_page=True)


def goto(page, path):
    print(f"goto:{path}", flush=True)
    page.goto(f"{BASE_URL}{path}", wait_until="domcontentloaded")
    page.wait_for_timeout(1800)


def login(page, username, password):
    print(f"login:{username}", flush=True)
    goto(page, "/login?lang=en")
    page.fill('input[name="email"]', username)
    page.fill('input[name="password"]', password)
    page.click('button[type="submit"]')
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_timeout(1800)


def set_itinerary_form(page):
    page.select_option('select[name="destination_city"]', "Riyadh")
    page.fill('input[name="duration_days"]', "3")
    page.evaluate(
        """
        () => {
          const budget = document.querySelector('input[name="budget"]');
          budget.value = "2500";
          budget.dispatchEvent(new Event('input', { bubbles: true }));
          document.querySelector('select[name="trip_type"]').value = 'cultural';
          document.querySelector('input[name="interests"]').value = 'cultural,history,museums';
        }
        """
    )


def ensure_demo_itinerary():
    print("ensure_demo_itinerary", flush=True)
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(email="user@wajhati.local").first()
        if not user:
            raise RuntimeError("Default demo user not found")
        existing = (
            Itinerary.query.filter_by(user_id=user.id)
            .order_by(Itinerary.id.desc())
            .first()
        )
        if existing:
            return existing.id

        itinerary = Itinerary(
            user_id=user.id,
            destination_city="Riyadh",
            trip_type="cultural",
            duration_days=3,
            budget=2500,
            interests="cultural, history, museums",
            estimated_total_cost=350,
        )
        db.session.add(itinerary)
        db.session.flush()
        items = [
            ItineraryItem(itinerary_id=itinerary.id, day_number=1, title="Historic Diriyah", notes="Explore heritage streets and museums.", estimated_cost=120),
            ItineraryItem(itinerary_id=itinerary.id, day_number=2, title="Kingdom Centre Sky Bridge", notes="Visit city landmark and shopping spaces.", estimated_cost=80),
            ItineraryItem(itinerary_id=itinerary.id, day_number=3, title="Edge of the World", notes="Outdoor trip with scenic desert views.", estimated_cost=150),
        ]
        db.session.add_all(items)
        db.session.commit()
        return itinerary.id


def capture_public_pages(page):
    pages = [
        ("/?lang=en", "index_public"),
        ("/destinations?lang=en", "destinations"),
        ("/destinations/1?lang=en", "destination_detail"),
        ("/map?lang=en", "map"),
        ("/login?lang=en", "login"),
        ("/register?lang=en", "register"),
    ]
    for path, name in pages:
        goto(page, path)
        shot(page, name)


def capture_user_pages(browser):
    print("capture_user_pages", flush=True)
    context = browser.new_context(viewport={"width": 1440, "height": 1800})
    page = context.new_page()
    itinerary_id = ensure_demo_itinerary()
    login(page, "user", "user")
    shot(page, "index_user")

    goto(page, "/profile?lang=en")
    shot(page, "profile")

    goto(page, "/itinerary/new?lang=en")
    shot(page, "create_itinerary_form")

    goto(page, "/my-itineraries?lang=en")
    shot(page, "my_itineraries")
    goto(page, f"/itineraries/{itinerary_id}?lang=en")
    shot(page, "itinerary_detail")
    context.close()


def capture_admin_pages(browser):
    print("capture_admin_pages", flush=True)
    context = browser.new_context(viewport={"width": 1440, "height": 1800})
    page = context.new_page()
    login(page, "admin", "admin")
    admin_pages = [
        ("/admin?lang=en", "admin_dashboard"),
        ("/admin/destinations?lang=en", "admin_destinations"),
        ("/admin/attractions?lang=en", "admin_attractions"),
        ("/admin/users?lang=en", "admin_users"),
        ("/admin/ai-settings?lang=en", "admin_ai_settings"),
    ]
    for path, name in admin_pages:
        goto(page, path)
        shot(page, name)
    context.close()


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1800})
        capture_public_pages(page)
        capture_user_pages(browser)
        capture_admin_pages(browser)
        browser.close()


if __name__ == "__main__":
    main()
