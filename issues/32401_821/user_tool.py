import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import logging
from playwright.sync_api import sync_playwright, expect
from playwright._impl._page import Page
from utils.trace_cleaner import trace_cleaner

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
EMAIL = "Adebayovicktor0+test42262@gmail.com"
PASSWORD = "bruzwjfovckiesys"
NEW_DOT_URL = "https://dev.new.expensify.com:8082"
OLD_DOT_URL = "http://localhost:9000/"
ONE_SECOND = 1000
TWO_SECONDS = 2000
THREE_SECONDS = 3000
FIVE_SECONDS = 5000


# Sign In to Expensify
def sign_in_new_dot(page: Page, email: str, url: str=None):
    """
    Sign in into the new Expensify dot.
    """
    # Go to URL
    url = url if url else NEW_DOT_URL
    page.goto(url)
    # Sign In
    page.get_by_test_id("username").fill(email)
    page.wait_for_timeout(TWO_SECONDS)
    page.get_by_role("button", name="Continue").click()
    page.wait_for_timeout(FIVE_SECONDS)
    # OTP is hardcoded for replay
    otp = '123456'
    page.get_by_test_id("validateCode").fill(otp)
    page.wait_for_timeout(TWO_SECONDS)

    # Wait sign in to complete
    page.get_by_text("Please enter the magic code").wait_for(state="hidden")
    page.wait_for_timeout(THREE_SECONDS)
    logging.info("Sign in complete.")

def test_popup():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True,
            proxy = {"server": "http://127.0.0.1:8080/"},
            args=[
            "--ignore-certificate-errors",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ]
        )
        context = browser.new_context()

        # Start tracing
        context.tracing.start(screenshots=True, snapshots=True, sources=True)

        page = context.new_page()
        try:
            # Step 1: Login user using the utility function
            sign_in_new_dot(page, EMAIL)

            textbox = page.get_by_test_id("report-actions-view-wrapper").get_by_role("textbox")
            textbox.clear()
            textbox.fill("@")
            expect(page.get_by_label("Notify everyone in this")).to_be_visible(timeout=100)

        except Exception as e:
            raise e
        finally:
            # Stop tracing and save
            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            # Clean the trace
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")

            page.close()
            browser.close()
