"""
Playwright end-to-end tests for destination browsing, favorites, reviews, and itinerary flows.

Selector improvement suggestions:
- Add `data-testid` markers for destination cards, favorite toggles, review forms, and itinerary cards.
- Give the itinerary budget input a dedicated text/number field for easier automated validation.
- Add English flash text for success/error toasts in `?lang=en` mode so assertions can be more specific.
"""

import re
import time

from playwright.sync_api import Page, expect


BASE_URL = "http://127.0.0.1:5000"


def unique_email(prefix: str = "feature") -> str:
    return f"{prefix}_{time.time_ns()}@example.com"


def register_and_login(page: Page, *, name: str = "Feature User", password: str = "Password123!") -> str:
    """Create a fresh user and log in so each test is isolated."""
    email = unique_email()

    page.goto(f"{BASE_URL}/register?lang=en")
    page.locator("input[name='name']").fill(name)
    page.locator("input[name='email']").fill(email)
    page.locator("input[name='password']").fill(password)
    page.locator("button[type='submit']").click()

    page.locator("input[name='email']").fill(email)
    page.locator("input[name='password']").fill(password)
    page.locator("button[type='submit']").click()

    expect(page.locator("[data-profile-toggle]")).to_be_visible()
    return email


def open_destination(page: Page, destination_name: str = "Historic Diriyah") -> None:
    """Navigate to a known seeded destination using the browse page."""
    page.goto(f"{BASE_URL}/destinations?lang=en")
    destination_link = page.get_by_role("link", name=re.compile(destination_name))
    expect(destination_link).to_be_visible()
    destination_link.click()


def set_budget(page: Page, value: str) -> None:
    """Update the range input in a way Playwright can control reliably."""
    page.locator("input[name='budget']").evaluate(
        """
        (element, nextValue) => {
            element.value = nextValue;
            element.dispatchEvent(new Event('input', { bubbles: true }));
            element.dispatchEvent(new Event('change', { bubbles: true }));
        }
        """,
        value,
    )


def test_browse_destinations_page_lists_seeded_records(page: Page) -> None:
    # The browse page should load and show destinations from the seeded demo dataset.
    page.goto(f"{BASE_URL}/destinations?lang=en")

    expect(page).to_have_url(re.compile(r".*/destinations\?lang=en$"))
    expect(page.get_by_role("heading", name="Explore Destinations")).to_be_visible()
    expect(page.get_by_role("link", name=re.compile("Historic Diriyah"))).to_be_visible()


def test_view_destination_details(page: Page) -> None:
    # Opening a destination should show the detail page, description, and review area.
    open_destination(page, "Historic Diriyah")

    expect(page).to_have_url(re.compile(r".*/destinations/\d+\?lang=en$"))
    expect(page.get_by_role("heading", name="Historic Diriyah")).to_be_visible()
    expect(page.get_by_role("heading", name="About Destination")).to_be_visible()
    expect(page.get_by_role("heading", name="Reviews")).to_be_visible()


def test_add_and_remove_favorite(page: Page) -> None:
    # Logged-in users should be able to toggle a destination as a favorite.
    register_and_login(page)
    open_destination(page, "Historic Diriyah")

    favorite_button = page.get_by_role("button", name="Add Favorite")
    expect(favorite_button).to_be_visible()
    favorite_button.click()

    expect(page.locator("[role='alert']")).to_be_visible()
    expect(page.get_by_role("button", name="Remove Favorite")).to_be_visible()

    page.get_by_role("button", name="Remove Favorite").click()

    expect(page.locator("[role='alert']")).to_be_visible()
    expect(page.get_by_role("button", name="Add Favorite")).to_be_visible()


def test_submit_review(page: Page) -> None:
    # Review submission should keep the user on the destination page and render the new comment.
    register_and_login(page)
    open_destination(page, "Historic Diriyah")

    unique_comment = f"Playwright review {time.time_ns()}"
    page.locator("input[name='rating']").fill("5")
    page.locator("textarea[name='comment']").fill(unique_comment)
    page.get_by_role("button", name="Submit Review").click()

    expect(page).to_have_url(re.compile(r".*/destinations/\d+\?lang=en$"))
    expect(page.locator("[role='alert']")).to_be_visible()
    expect(page.get_by_text(unique_comment)).to_be_visible()


def test_generate_itinerary_with_valid_input(page: Page) -> None:
    # A valid itinerary request should redirect to the itinerary detail page and render trip items.
    register_and_login(page)
    page.goto(f"{BASE_URL}/itinerary/new?lang=en")

    page.locator("select[name='destination_city']").select_option("Riyadh")
    page.locator("input[name='duration_days']").fill("2")
    set_budget(page, "2000")
    page.locator("select[name='trip_type']").select_option("family")
    page.locator("input[name='interests']").fill("cultural, leisure")
    page.locator("button[type='submit']").click()

    expect(page).to_have_url(re.compile(r".*/itineraries/\d+$"))
    expect(page.locator("[role='alert']")).to_be_visible()
    expect(page.get_by_role("heading", name=re.compile(r"Riyadh Trip #\d+"))).to_be_visible()
    expect(page.get_by_text("Day 1")).to_be_visible()


def test_itinerary_missing_city_shows_validation(page: Page) -> None:
    # Missing city is currently blocked by native browser validation on the required select element.
    register_and_login(page)
    page.goto(f"{BASE_URL}/itinerary/new?lang=en")

    page.locator("input[name='duration_days']").fill("2")
    set_budget(page, "2000")
    page.locator("select[name='trip_type']").select_option("family")
    page.locator("input[name='interests']").fill("cultural")
    page.locator("button[type='submit']").click()

    city_message = page.locator("select[name='destination_city']").evaluate("el => el.validationMessage")

    expect(page).to_have_url(re.compile(r".*/itinerary/new\?lang=en$"))
    assert city_message


def test_itinerary_bad_budget_shows_server_error(page: Page) -> None:
    # Force an invalid budget value and assert the server-side validation message appears.
    register_and_login(page)
    page.goto(f"{BASE_URL}/itinerary/new?lang=en")

    page.locator("select[name='destination_city']").select_option("Riyadh")
    page.locator("input[name='duration_days']").fill("2")
    page.locator("input[name='budget']").evaluate(
        """
        (element) => {
            element.type = 'number';
            element.min = '-1000';
            element.max = '10000';
            element.value = '-10';
        }
        """
    )
    page.locator("select[name='trip_type']").select_option("family")
    page.locator("input[name='interests']").fill("cultural")
    page.locator("button[type='submit']").click()

    expect(page).to_have_url(re.compile(r".*/itinerary/new\?lang=en$"))
    expect(page.locator("[role='alert']")).to_be_visible()
    expect(page.locator("[role='alert']")).to_contain_text("Budget must be greater than 0.")
