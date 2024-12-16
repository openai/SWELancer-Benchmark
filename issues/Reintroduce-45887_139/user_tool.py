import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import Page, expect, sync_playwright
from utils.trace_cleaner import trace_cleaner

# Utility to generate a random email
def generate_random_email(timestamp: str):
    return f"freelanceapptest+{timestamp}@gmail.com"


def create_user(
    page: Page, firstname: str, lastname: str, timestamp: str):
    # Sign up
    page.get_by_test_id("username").fill(generate_random_email(timestamp))
    page.get_by_role("button", name="Continue").click()
    page.get_by_role("button", name="Join").click()

    # Update profile
    page.get_by_text("Track and budget expenses").click()
    page.get_by_role("textbox", name="First name").fill(firstname)
    page.get_by_role("textbox", name="Last name").fill(lastname)
    page.get_by_role("button", name="Continue").click()


def close_button_if_present(page: Page):
    """
    Occasionally, there is a close button that prevents any clicks on the page as
    it covers most of the screen. This button cannot be seen visually.
    """
    close_button = page.locator('button[aria-label="Close"]')
    if close_button.is_visible():
        close_button.click()


def test_error_message():

    with sync_playwright() as p:
        timestamp = 1221000012344

        # Launch chromium and open new page
        phone = p.devices["Galaxy S9+"]
        browser = p.chromium.launch(headless=True, slow_mo=1000, args=[
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
        ])
        context = browser.new_context(**phone, ignore_https_errors=True)

        # Start tracing
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        try:
            page = context.new_page()
            page.goto("https://dev.new.expensify.com:8082/")

            # create user
            create_user(page, "TestUser", f"{timestamp}", timestamp)

            # Enable default workspace
            close_button_if_present(page)
            page.get_by_label("My settings").click()
            page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()
            page.get_by_label("New workspace").first.click()
            page.get_by_label("Back").last.click()
            page.get_by_label("Back").last.click()

            # Enable taxes
            close_button_if_present(page)
            page.get_by_label("My settings").click()
            page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()
            page.get_by_label("row").click()
            page.get_by_label("More features").click()
            page.get_by_label("Document and reclaim eligible").click()

            # Add tax-rate
            page.get_by_label("Taxes").click()
            page.get_by_role("button", name="Add rate").click()
            page.get_by_role("menuitem", name="Name Required").click()
            page.get_by_role("textbox", name="Name").fill("<h>")
            page.get_by_test_id("TextSelectorModal").get_by_role("button", name="Save").click()

            # Expect an error message
            expect(page.get_by_text("Invalid character")).to_be_visible()
        finally:
            # Stop tracing & export
            context.tracing.stop()
            trace_path = '/app/expensify/user_tool/output_browser1.zip'
            context.tracing.export(trace_path)
            # Clean the trace
            trace_cleaner(trace_path)

            context.close()
            browser.close()
