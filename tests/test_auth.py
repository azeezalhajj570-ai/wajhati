"""
Playwright end-to-end tests for authentication and form validation flows.

Selector improvement suggestions:
- Add `data-testid` attributes for flash toasts, profile menu, and auth submit buttons.
- Add a `confirm_password` input to the signup form so mismatch validation can be tested properly.
- Add explicit password rules such as `minlength="8"` and matching server-side validation.
- Normalize auth flash messages to consistent English text in `?lang=en` mode for stronger assertions.
"""

import re
import time
from typing import Optional

import pytest
from playwright.sync_api import Page, expect


BASE_URL = "http://127.0.0.1:5000"


def unique_email(prefix: str = "playwright") -> str:
    return f"{prefix}_{time.time_ns()}@example.com"


def register_user(page: Page, *, name: str = "Playwright User", email: Optional[str] = None, password: str = "Password123!") -> str:
    """Create a unique user through the real signup form."""
    email = email or unique_email()
    page.goto(f"{BASE_URL}/register?lang=en")
    page.locator("input[name='name']").fill(name)
    page.locator("input[name='email']").fill(email)
    page.locator("input[name='password']").fill(password)
    page.locator("button[type='submit']").click()
    return email


def login_user(page: Page, *, email: str, password: str = "Password123!") -> None:
    """Log in through the real login form."""
    page.goto(f"{BASE_URL}/login?lang=en")
    page.locator("input[name='email']").fill(email)
    page.locator("input[name='password']").fill(password)
    page.locator("button[type='submit']").click()


def open_profile_menu(page: Page) -> None:
    """Open the top-right profile menu before clicking logout."""
    page.locator("[data-profile-toggle]").click()
    expect(page.locator("[data-profile-menu]")).to_be_visible()


def test_signup_valid_case_redirects_to_login(page: Page) -> None:
    # Valid signup should submit successfully, redirect to login, and show a flash alert.
    register_user(page)

    expect(page).to_have_url(re.compile(r".*/login(\?lang=en)?$"))
    expect(page.locator("[role='alert']")).to_be_visible()
    expect(page.locator("input[name='email']")).to_be_visible()


def test_login_valid_credentials(page: Page) -> None:
    # Register first so the test is fully independent, then log in with that user.
    email = register_user(page)
    login_user(page, email=email)

    expect(page).to_have_url(re.compile(r".*/(\?lang=en)?$"))
    expect(page.locator("[role='alert']")).to_be_visible()
    expect(page.locator("[data-profile-toggle]")).to_be_visible()


def test_login_failure_with_wrong_password(page: Page) -> None:
    # Wrong credentials should keep the user on the login page and show an error flash.
    email = register_user(page)

    page.goto(f"{BASE_URL}/login?lang=en")
    page.locator("input[name='email']").fill(email)
    page.locator("input[name='password']").fill("WrongPassword123!")
    page.locator("button[type='submit']").click()

    expect(page).to_have_url(re.compile(r".*/login(\?lang=en)?$"))
    expect(page.locator("[role='alert']")).to_be_visible()
    expect(page.locator("input[name='password']")).to_be_visible()


def test_logout_clears_authenticated_navigation(page: Page) -> None:
    # After login, logout should redirect home and remove the authenticated profile menu.
    email = register_user(page)
    login_user(page, email=email)
    open_profile_menu(page)
    page.locator("[data-profile-menu] a[href='/logout']").click()

    expect(page).to_have_url(re.compile(r".*/$"))
    expect(page.locator("[role='alert']")).to_be_visible()
    expect(page.locator("[data-profile-toggle]")).to_have_count(0)
    expect(page.locator("a[href*='/login']")).to_be_visible()


def test_signup_required_fields_show_browser_validation(page: Page) -> None:
    # Empty required signup fields should be blocked by browser validation before submit.
    page.goto(f"{BASE_URL}/register?lang=en")
    page.locator("button[type='submit']").click()

    name_message = page.locator("input[name='name']").evaluate("el => el.validationMessage")
    email_message = page.locator("input[name='email']").evaluate("el => el.validationMessage")
    password_message = page.locator("input[name='password']").evaluate("el => el.validationMessage")

    expect(page).to_have_url(re.compile(r".*/register\?lang=en$"))
    assert any([name_message, email_message, password_message])


def test_signup_invalid_email_shows_browser_validation(page: Page) -> None:
    # Invalid email format should trigger the native email input validation message.
    page.goto(f"{BASE_URL}/register?lang=en")
    page.locator("input[name='name']").fill("Validation User")
    page.locator("input[name='email']").fill("not-an-email")
    page.locator("input[name='password']").fill("Password123!")
    page.locator("button[type='submit']").click()

    email_message = page.locator("input[name='email']").evaluate("el => el.validationMessage")

    expect(page).to_have_url(re.compile(r".*/register\?lang=en$"))
    assert email_message


@pytest.mark.xfail(
    reason="Current signup form has no confirm_password field or mismatch validation.",
    strict=False,
)
def test_signup_confirm_password_mismatch_shows_error(page: Page) -> None:
    # This is the desired test once confirm-password support exists in the form and backend.
    page.goto(f"{BASE_URL}/register?lang=en")
    page.locator("input[name='name']").fill("Mismatch User")
    page.locator("input[name='email']").fill(unique_email("mismatch"))
    page.locator("input[name='password']").fill("Password123!")
    page.locator("input[name='confirm_password']").fill("DifferentPassword123!")
    page.locator("button[type='submit']").click()

    expect(page).to_have_url(re.compile(r".*/register(\?lang=en)?$"))
    expect(page.locator("[role='alert']")).to_be_visible()


@pytest.mark.xfail(
    reason="Current signup form has no short-password validation in HTML or server-side route logic.",
    strict=False,
)
def test_signup_short_password_shows_error(page: Page) -> None:
    # This is the desired test once password length rules are added to the product.
    page.goto(f"{BASE_URL}/register?lang=en")
    page.locator("input[name='name']").fill("Short Password User")
    page.locator("input[name='email']").fill(unique_email("shortpwd"))
    page.locator("input[name='password']").fill("123")
    page.locator("button[type='submit']").click()

    expect(page).to_have_url(re.compile(r".*/register(\?lang=en)?$"))
    expect(page.locator("[role='alert']")).to_be_visible()


def test_form_error_feedback_is_visible_for_login_failure(page: Page) -> None:
    # A failed login should render a visible flash toast so the user sees feedback immediately.
    page.goto(f"{BASE_URL}/login?lang=en")
    page.locator("input[name='email']").fill("missing-user@example.com")
    page.locator("input[name='password']").fill("WrongPassword123!")
    page.locator("button[type='submit']").click()

    expect(page).to_have_url(re.compile(r".*/login(\?lang=en)?$"))
    expect(page.locator("[role='alert']")).to_be_visible()
