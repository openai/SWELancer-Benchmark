import time
import pytest
from playwright.sync_api import (
    sync_playwright,
    Page,
    TimeoutError as PlaywrightTimeoutError,
)

def generate_random_email():
    # return f"t56826807+{int(time.time())}@gmail.com"
    return "t56826807+1740054508@gmail.com"

@pytest.fixture
def setup_playwright():
    playwright = sync_playwright().start()

    browser = playwright.chromium.launch(
        headless=False,
        args=[
            "--ignore-certificate-errors",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
        ],
        proxy={"server": "http://localhost:8080"},
        slow_mo=500,
    )
    context = browser.new_context(
        **playwright.devices["iPhone 12"],
        locale="en-US",
    )
    page = context.new_page()

    yield page

    # Cleanup: close browsers and stop Playwright
    browser.close()
    playwright.stop()


def login_user(page: Page, email: str):
    page.goto("https://dev.new.expensify.com:8082/")
    page.locator('input[type="email"]').fill(email)
    page.locator("button", has_text="Continue").click()
    page.locator("button", has_text="Join").click()


def complete_onboarding(page: Page, first_name: str, last_name: str = ""):
    page.locator("text='Track and budget expenses'").click()
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()


def swipe(page: Page, direction: str):
    """
    Simulates a swipe gesture using mouse events.

    :param page: Playwright Page instance.
    :param direction: "left" or "right".
    """
    viewport = page.viewport_size
    if not viewport:
        raise ValueError("Viewport size not available")

    # Determine swipe positions based on direction
    if direction == "right":
        start_x, end_x = viewport["width"] // 4, (viewport["width"] * 3) // 4
    elif direction == "left":
        start_x, end_x = (viewport["width"] * 3) // 4, viewport["width"] // 4
    else:
        raise ValueError("Direction must be 'left' or 'right'.")

    y = viewport["height"] // 2  # Swipe in the middle of the screen

    # Perform swipe using mouse actions
    page.mouse.move(start_x, y)
    page.mouse.down()
    page.mouse.move(end_x, y, steps=5)  # Move with smooth motion
    page.mouse.up()


def test(setup_playwright):
    page = setup_playwright

    email_user, name_user = generate_random_email(), "User A"

    login_user(page, email_user)

    complete_onboarding(page, name_user)

    page.get_by_label("Start chat (Floating action)").click()
    try:
        page.get_by_text("Create expense").click(timeout=1000)
    except Exception:
        page.get_by_text("Submit expense").click(timeout=1000)

    page.wait_for_timeout(1000)
    swipe(page, 'right')

    manual_tab = page.locator('button[aria-label="Scan"]')
    bg_color = manual_tab.evaluate("el => window.getComputedStyle(el).backgroundColor")

    # Assert the expected color
    assert bg_color != "rgb(230, 225, 218)", (
        f"Scan expense tab still highlighted: {bg_color}"
    )