import pytest
from playwright.sync_api import sync_playwright


@pytest.fixture(scope="session")
def playwright_instance():
    """Start Playwright once for the full test session."""
    with sync_playwright() as playwright:
        yield playwright


@pytest.fixture(scope="session")
def browser(playwright_instance):
    """Launch a shared Chromium browser for all UI tests."""
    browser = playwright_instance.chromium.launch(headless=True)
    yield browser
    browser.close()


@pytest.fixture()
def page(browser):
    """Create a fresh isolated page for each test so cases stay independent."""
    context = browser.new_context(base_url="http://127.0.0.1:5000")
    page = context.new_page()
    yield page
    context.close()
