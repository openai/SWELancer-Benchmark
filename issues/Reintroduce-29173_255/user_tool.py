import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

"""
Tests for the issue: https://github.com/Expensify/App/issues/29173
"""

import time
from playwright.sync_api import expect, sync_playwright
from utils.trace_cleaner import trace_cleaner

# Expensify app URL
EXPENSIFY_URL = "https://dev.new.expensify.com:8082/"


def launch_app(pw):
    """
    Launch the Expensify app.
    """
    browser = pw.chromium.launch(
        channel="chrome",
        headless=True,
        args=[
            "--ignore-certificate-errors",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ],
        proxy={"server": "http://localhost:8080"},
        slow_mo=1000
    )

    context_args = {
        "timezone_id": "America/Los_Angeles",
    }

    context = browser.new_context(**context_args)
    page = context.new_page()

    page.goto(EXPENSIFY_URL)
    return browser, context, page


def login_user(page, email, first_name="Jane", last_name="Doe"):
    """
    Login to the Expensify app and complete the onboarding.
    """
    # Login user
    page.locator("input[type='email']").fill(email)
    page.get_by_role("button", name="Continue").click()
    page.get_by_role("button", name="Join").click()

    # Complete onboarding
    page.get_by_text("Track and budget expenses").click()
    page.locator("input[name='fname']").fill(first_name)
    page.locator("input[name='lname']").fill(last_name)
    page.get_by_role("button", name="Continue").click()


def test_new_line_for_first_interaction_between_two_users():
    """
    Verify that when User A sends a message to User B (first iteraction), the message is displayed juest after a new line.
    """
    with sync_playwright() as pw:
        # User A (sender): Launch the app and login
        email_a = "checkissue86+29173@gmail.com"
        browser_a, context_a, page_a = launch_app(pw)
        context_a.tracing.start(screenshots=True, snapshots=True, sources=True)

        # User B (receiver): Launch the app and login
        email_b = "checkissue75+29173@gmail.com"
        browser_b, context_b, page_b = launch_app(pw)
        context_b.tracing.start(screenshots=True, snapshots=True, sources=True)

        try:
            login_user(page_a, email_a, "User A", "Sender")
            login_user(page_b, email_b, "User B", "Receiver")

            # Click on "Create" button (+)
            page_a.get_by_label("Start chat (Floating action)").click()

            # Click on "Start chat" button
            page_a.get_by_text("Start chat").click()

            # Input the email of User B (receiver)
            expect(page_a.get_by_test_id("selection-list-text-input")).to_be_visible()
            page_a.get_by_test_id("selection-list-text-input").fill(email_b)

            # Add User B (receiver) to the chat
            expect(page_a.get_by_role("button", name="Add to group")).to_be_visible()
            page_a.get_by_role("button", name="Add to group").click()  # Select User B
            page_a.get_by_role("button", name="Next").click()  # Click on "Next" button

            # Create the chat
            expect(page_a.get_by_role("button", name="Start group")).to_be_visible()
            page_a.get_by_role("button", name="Start group").click()

            # Send a message from User A to User B
            expect(page_a.get_by_role("textbox")).to_be_visible()
            page_a.get_by_role("textbox").fill("Hello, User B!")
            page_a.get_by_role("textbox").press("Enter")

            # User B expects to see the message from User A
            expect(page_b.locator('[data-testid="DisplayNamesWithTooltip"]:text("User A, User B")')).to_be_visible(timeout=15000)
            page_b.locator('[data-testid="DisplayNamesWithTooltip"]:text("User A, User B")').click()

            # Assert that the message is displayed just after a new line
            assert page_b.locator('div[aria-label="New message line indicator"]').count() == 1, "New line indicator is not visible"
        except Exception as e:
            # Re-raise the exception so Playwright test frameworks can see it
            raise e
        finally:
            # Stop tracing and clean traces for both contexts
            context_a.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")

            context_b.tracing.stop(path="/app/expensify/user_tool/output_browser2.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser2.zip")

            # Close the browsers
            context_a.close()
            browser_a.close()
            context_b.close()
            browser_b.close()
