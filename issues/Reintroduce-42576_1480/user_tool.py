import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from playwright._impl._page import Page
from utils.trace_cleaner import trace_cleaner

# Utility to generate a random email
timestamp_1 = 12021
username_1 = f"redx224+{timestamp_1}"


# Utility to generate a random email
def generate_random_email(timestamp: int):
    return f"redx224+{timestamp}@gmail.com"


def create_user(page: Page, timestamp: int, firstname: str, lastname: str) -> None:
    # join user #1

    email = generate_random_email(timestamp)
    page.get_by_test_id("username").fill(email)
    page.get_by_role("button", name="Continue").click()
    page.wait_for_timeout(2000)
    page.get_by_role("button", name="Join").click()

    try:
        # Update profile
        page.get_by_text("Track and budget expenses").click()
        page.get_by_role("button", name="Continue").nth(0).click()
        page.get_by_role("textbox", name="First name").fill(firstname)
        page.get_by_role("textbox", name="Last name").fill(lastname)
        page.get_by_role("button", name="Continue").nth(1).click()
    except:
        pass

    return email


def test_issue_42576():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=[
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
        ])
        context_1 = browser.new_context()

        # Start tracing
        context_1.tracing.start(screenshots=True, snapshots=True, sources=True)
        page = context_1.new_page()
        try:
            # create users
            page.goto("https://dev.new.expensify.com:8082/")
            email_1 = create_user(page, timestamp_1, "User", "A")

            page.get_by_role("button", name="Get Started").click()

            fab = page.locator('button[aria-label="Start chat (Floating action)"]')
            fab.click()
            page.wait_for_timeout(500)

            chat = page.get_by_text("New workspace").nth(0)
            chat.click()
            page.wait_for_timeout(500)

            features = page.get_by_text("More features").nth(0)
            features.click()
            page.wait_for_timeout(500)
            page.get_by_label("Configure how spend is").click()
            page.wait_for_timeout(500)
            page.get_by_text("Workflows").nth(0).click()
            page.wait_for_timeout(500)
            page.get_by_label("Require additional approval").click()
            page.wait_for_timeout(500)
            page.get_by_label("Approver").get_by_text("User A").click()
            page.wait_for_timeout(500)
            page.get_by_test_id("selection-list-text-input").fill(email_1)
            page.wait_for_timeout(500)
            name = page.get_by_label("User A")
            expect(name).to_be_visible()
        finally:
            # Stop tracing and clean
            context_1.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")

        browser.close()
