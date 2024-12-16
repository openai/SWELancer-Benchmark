import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
import pytest
from playwright.sync_api import sync_playwright, Page

email = "checkissue58+44210@gmail.com"

@pytest.fixture
def setup_playwright(request):
    width = getattr(request, "param", {}).get("width", 1280)
    height = getattr(request, "param", {}).get("height", 720)

    playwright = sync_playwright().start()
    viewport = {"width": width, "height": height}

    browser = playwright.chromium.launch(
        channel="chrome",
        headless=True,
        args=[
            "--ignore-certificate-errors",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ],
        proxy={"server": "http://localhost:8080"},
        slow_mo = 1000
    )

    context = browser.new_context(viewport={"width": width, "height": height})
    page = context.new_page()

    yield page

    # Cleanup
    browser.close()
    playwright.stop()


def login_user(page: Page, email: str, first_name: str, last_name: str):
    page.goto("https://dev.new.expensify.com:8082/")
    page.locator('input[type="email"]').fill(email)
    page.locator('button[tabindex="0"]').click()
    try:
        page.locator("button", has_text="Join").click()
    except Exception:
        pass
    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()
    
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()
    


def check_if_wrapped(element):
    is_wrapped = element.evaluate(
        """(element) => {
            const lineHeight = parseFloat(getComputedStyle(element).lineHeight);
            const lines = element.clientHeight / lineHeight;
            return lines > 1;
        }"""
    )

    return is_wrapped


@pytest.mark.parametrize(
    "setup_playwright",
    [{"width": 375, "height": 812}],  # Samsung Z Fold 5's front display dimensions
    indirect=True,
)
def test_workspaces_header(setup_playwright):
    page = setup_playwright
    first_name, last_name = "Test", "User"

    login_user(page, email, first_name, last_name)

    page.locator('button[aria-label="Close"]').click()

    page.locator('button[aria-label="My settings"]').click()
    page.locator('div[aria-label="Workspaces"]').click()

    back_button = page.locator("#backButton")
    parent_element = back_button.locator("..")
    workspaces_div = parent_element.locator("div", has_text="Workspaces").last

    if workspaces_div.count() == 0:
        print("No 'Workspaces' div found.")
        return None

    is_wrapped = check_if_wrapped(workspaces_div)

    assert not is_wrapped, "Workspaces header is wrapped into multiple lines!"


