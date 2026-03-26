import os
import socket
import sys
import threading
import time
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from wajhati import create_app


DEFAULT_HOST = "127.0.0.1"


def _wait_for_server(host: str, port: int, timeout: float = 10.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError(f"Timed out waiting for test server at {host}:{port}")


@pytest.fixture(scope="session")
def live_server(tmp_path_factory):
    """Run the Flask app locally so Playwright can exercise real pages."""
    db_path = tmp_path_factory.mktemp("playwright-data") / "ui-tests.db"
    previous_database_url = os.environ.get("DATABASE_URL")
    previous_secret_key = os.environ.get("SECRET_KEY")

    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["SECRET_KEY"] = "playwright-test-secret"

    app = create_app()
    server = make_server(DEFAULT_HOST, 0, app)
    port = server.server_port
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    _wait_for_server(DEFAULT_HOST, port)

    try:
        yield f"http://{DEFAULT_HOST}:{port}"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        if previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_database_url
        if previous_secret_key is None:
            os.environ.pop("SECRET_KEY", None)
        else:
            os.environ["SECRET_KEY"] = previous_secret_key


@pytest.fixture(scope="session")
def server_base_url(live_server):
    return live_server


@pytest.fixture
def configured_base_url(server_base_url):
    for module_name in ("tests.test_auth", "tests.test_features", "test_auth", "test_features"):
        module = sys.modules.get(module_name)
        if module is not None:
            module.BASE_URL = server_base_url


@pytest.fixture(scope="session")
def playwright_instance(server_base_url):
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
def page(browser, server_base_url, configured_base_url):
    """Create a fresh isolated page for each test so cases stay independent."""
    context = browser.new_context(base_url=server_base_url)
    page = context.new_page()
    yield page
    context.close()
