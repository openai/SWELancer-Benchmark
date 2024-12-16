import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import Page, sync_playwright
from utils.trace_cleaner import trace_cleaner


def create_user(
    page: Page, firstname: str, lastname: str):
    page.get_by_test_id("username").fill("testotpveriff+456333@gmail.com")
    page.wait_for_timeout(1000)
    page.get_by_role("button", name="Continue").click()
    page.wait_for_timeout(1000)
    page.get_by_role("button", name="Join").click()

    page.get_by_text("Track and budget expenses").click()
    page.get_by_role("textbox", name="First name").fill(firstname)
    page.get_by_role("textbox", name="Last name").fill(lastname)
    page.wait_for_timeout(1000)
    page.get_by_role("button", name="Continue").click()


def test_track_sound():

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True,  args=[
            '--ignore-certificate-errors',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
        ])
        context = browser.new_context()

        # Start tracing
        context.tracing.start(screenshots=True, snapshots=True)
        try:
            page = context.new_page()

            page.goto("https://dev.new.expensify.com:8082/")

            create_user(page, "Test", "User")
            page.wait_for_timeout(2000)

            page.get_by_label("Start chat (Floating action)").click()
            page.get_by_label("Track expense").click()
            page.get_by_role("button", name="Got it").click()
            page.get_by_label("Manual").click()
            page.get_by_placeholder("0").fill("1000")
            page.locator("#numPadContainerView").get_by_role("button", name="Next").click()
            page.get_by_label("Show more").click()
            page.get_by_role("menuitem", name="Merchant").click()
            page.get_by_role("textbox", name="Merchant").fill("merchant_1")
            page.get_by_role("button", name="Save").click()

            page.evaluate(
                """
              () => {
                window.soundPlayCount = 0;
                const originalPlay = Sound.prototype.create;
                Sound.prototype.create = function() {
                  originalPlay.call(this);
                  window.soundPlayCount++;
                };
              }
            """
            )

            page.get_by_role("button", name="Track expense").click()
            page.wait_for_timeout(2000)

            sound_play_count = page.evaluate("window.soundPlayCount")

            assert sound_play_count == 1, "Sound was not played once"
        except Exception as e:
            # Re-raise after any cleanup if needed
            raise e
        finally:
            # Stop tracing and save
            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            context.close()
            browser.close()
