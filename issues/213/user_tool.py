import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time

from playwright.sync_api import Page, expect, sync_playwright
from utils.trace_cleaner import trace_cleaner



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

    page.get_by_test_id("username").fill(generate_random_email())
    page.wait_for_timeout(1000)
    page.get_by_role("button", name="Continue").click()
    page.wait_for_timeout(1000)
    page.get_by_role("button", name="Join").click()


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

        context.tracing.start(title="emoji_picker_test_trace", screenshots=True, snapshots=True)

        page = context.new_page()

        try:
            page.goto("https://dev.new.expensify.com:8082/")


            create_user(page, "TestUser", "me")
            page.wait_for_timeout(1000)


            close_button_if_present(page)
            page.locator('button[aria-label="Navigates to a chat"]').nth(1).click()
            page.get_by_role("textbox").fill(":pizza")


            expect(page.get_by_label("pizza+0}")).to_be_visible()


            close_button_if_present(page)  # Hide emoji picker
            page.keyboard.press("Enter")


            pizza_text = page.locator('span:has-text(":pizza")').inner_text()

            page.get_by_role("textbox").fill(pizza_text)
            page.wait_for_timeout(1000)


            expect(page.get_by_label("pizza+0}")).to_be_visible()


            assert not "\u2066" in pizza_text, "Text should not contain '\u2066'"

        except Exception as e:
            print("Test failed:", str(e))
            raise
        finally:

            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")

            context.close()
            browser.close()
