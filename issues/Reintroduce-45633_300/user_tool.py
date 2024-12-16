import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
from playwright.sync_api import Page, expect, sync_playwright
from utils.trace_cleaner import trace_cleaner


# Utility to generate a random email
def generate_random_email(timestamp: int = int(time.time())):
    return f"t56826807+{timestamp}@gmail.com"


def create_user(
    page: Page, firstname: str, lastname: str, timestamp: int = int(time.time())
):
    # Sign up
    page.get_by_test_id("username").fill(generate_random_email(timestamp))
    page.get_by_role("button", name="Continue").click()
    page.get_by_role("button", name="Join").click()

    # Update profile
    page.get_by_text("Track and budget expenses").click()
    page.get_by_role("textbox", name="First name").fill(firstname)
    page.get_by_role("textbox", name="Last name").fill(lastname)
    page.get_by_role("button", name="Continue").click()


def test_track_sound():
    with sync_playwright() as p:
        timestamp = 1733998335

        # Launch chromium and open new page
        browser = p.chromium.launch(
            channel="chrome",
            headless=True,
            args=[
                "--ignore-certificate-errors",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
            ],
            proxy={"server": "http://localhost:8080"},
            slow_mo=500,
        )
        context_args = {}
        context_args["timezone_id"] = "Asia/Karachi"
        context = browser.new_context(**context_args)

        # Start recording trace
        context.tracing.start(screenshots=True, snapshots=True, sources=True)

        page = context.new_page()

        try:
            page.goto("https://dev.new.expensify.com:8082/")

            # create user
            create_user(page, "TestUser", f"{timestamp}", timestamp)

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

            # Override the create method of the Sound object
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

            # Check how many times the sound was played
            sound_play_count = page.evaluate("window.soundPlayCount")

            # expect sound to be played once
            assert sound_play_count == 1, "Sound was not played once"
        except Exception as e:
            raise e
        finally:
            # Stop trace and save it
            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            # Clean the trace
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")

            context.close()
            browser.close()
