import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time

from playwright.sync_api import Page, expect, sync_playwright
from utils.trace_cleaner import trace_cleaner


# Utility to generate a random email
def generate_random_email(timestamp: int = int(time.time())):
    return f"testerbro7077+86675667@gmail.com"


def create_user(
    page: Page, firstname: str, lastname: str = None, timestamp: int = None
):
    page.evaluate("""
        Onyx.merge('nvp_onboarding', { hasCompletedGuidedSetupFlow: false });
            """)

    page.reload()
    page.wait_for_timeout(1000)
    timestamp = timestamp or int(time.time())
    # Sign up
    page.get_by_test_id("username").fill(generate_random_email())
    page.wait_for_timeout(1000)
    page.get_by_role("button", name="Continue").click()
    page.wait_for_timeout(1000)
    page.get_by_role("button", name="Join").click()

    # Update profile
    page.get_by_text("Track and budget expenses").click()
    page.get_by_role("textbox", name="First name").fill(firstname)
    page.get_by_role("textbox", name="Last name").fill(lastname)
    page.wait_for_timeout(1000)
    page.get_by_role("button", name="Continue").click()


def close_button_if_present(page: Page):
    """
    Occasionally, there is a close button that prevents any clicks on the page as
    it covers most of the screen. This button cannot be seen visually.
    """
    close_button = page.locator('button[aria-label="Close"]')
    if close_button.is_visible():
        close_button.click()


def test_emoji_picker():
    with sync_playwright() as p:
        timestamp = int(time.time())
        
        browser = p.chromium.launch(channel="chrome", headless=True, args=[
             "--disable-web-security",
             "--disable-features=IsolateOrigins,site-per-process"
        ])
        context = browser.new_context()

        # Start tracing
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        trace_path = "/app/expensify/user_tool/output_browser1.zip"

        try:
            page = context.new_page()
            page.goto("https://dev.new.expensify.com:8082/")

            # create user
            create_user(page, "TestUser", "me")
            page.wait_for_timeout(1000)

            # Send message to self
            close_button_if_present(page)
            page.locator('button[aria-label="Navigates to a chat"]').nth(1).click()
            page.get_by_role("textbox").fill(":pizza")

            # Emoji picker should show up
            expect(page.get_by_label("pizza+0}")).to_be_visible()

            # Click send button
            close_button_if_present(page)  # Hide emoji picker
            page.keyboard.press("Enter")

            # Select div containing :pizza text
            pizza_text = page.locator('span:has-text(":pizza")').inner_text()

            page.get_by_role("textbox").fill(pizza_text)
            page.wait_for_timeout(1000)

            # Emoji picker should show up from pasting copied text
            expect(page.get_by_label("pizza+0}")).to_be_visible()

            # check if pizza text contains '\u2066'
            assert "\u2066" not in pizza_text, "Text should not contain '\u2066'"
        except Exception as e:
            # Re-raise the exception so the test fails normally
            raise e
        finally:
            # Stop and export the trace
            context.tracing.stop()
            context.tracing.export(path=trace_path)
            trace_cleaner(trace_path)

        context.close()
        browser.close()
