import time
import pytest
from playwright.sync_api import (
    sync_playwright,
    Page,
    TimeoutError as PlaywrightTimeoutError,
)
from utils.trace_cleaner import trace_cleaner


def generate_random_email():
    # return f"t56826807+{int(time.time())}@gmail.com"
    return "t56826807+1739787921@gmail.com"
   

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

    # Yield all necessary objects for further control in the test function
    yield browser, context, page, playwright

    # Fixture cleanup (wrapped in try/except to ignore errors if already closed)
    try:
        browser.close()
    except Exception:
        pass
    try:
        playwright.stop()
    except Exception:
        pass


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


def test(setup_playwright):
    # Unpack the objects from the fixture
    browser, context, page, playwright = setup_playwright

    # Start tracing session
    context.tracing.start(screenshots=True, snapshots=True, sources=True)

    try:
        email_user, name_user = generate_random_email(), "User A"

        login_user(page, email_user)

        complete_onboarding(page, name_user)

        page.get_by_label("Back").last.click()
        page.get_by_label("Start chat (Floating action)").click()
        try:
            page.get_by_label("Create expense").click(timeout=2000)
        except Exception:
            page.get_by_label("Submit expense").click()
            
        page.get_by_label("Manual").click()
        try:
            page.get_by_role("button", name="<").click(timeout=2000)
            raise AssertionError("Button with text '<' found!")
        except PlaywrightTimeoutError:
            pass
    finally:
        trace_file = "/app/expensify/user_tool/output_browser1.zip"
        # Stop tracing and export the trace file
        context.tracing.stop(path=trace_file)
        
        # Clean the exported trace
        trace_cleaner(trace_file)
        
        # Close the browser and stop Playwright
        browser.close()
        playwright.stop()