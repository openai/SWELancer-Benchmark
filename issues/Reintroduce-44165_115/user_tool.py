import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

"""
Tests for the issue: https://github.com/Expensify/App/issues/44165
"""

import logging
import sys
from playwright.sync_api import TimeoutError, expect, sync_playwright
from utils.trace_cleaner import trace_cleaner

# Expensify app URL
EXPENSIFY_URL = "https://dev.new.expensify.com:8082/"

# Email login credentials
EMAIL_USERNAME = "expensifytesting1@gmail.com"
EMAIL_PASSWORD = "redx tbmr hzpc rbzr"

# Email username postfix
EMAIL_USERNAME_POSTFIX = "44165.1"

# Logger
logging.basicConfig(level=logging.INFO, stream=sys.stdout, format="%(message)s")
LOGGER = logging.getLogger(__name__)


def generate_user_email(user_id=None):
    """
    Generate an email address for a user login.
    """
    temp = EMAIL_USERNAME.rsplit("@", 1)
    username = temp[0].strip()
    domain = temp[1].strip()
    return f"{username}+{EMAIL_USERNAME_POSTFIX}{user_id or ''}@{domain}"


def launch_browser(pw, headless=True, device=None, geolocation=None):
    """
    Launch the browser.
    """
    browser = pw.chromium.launch(headless=headless, slow_mo=1000, args=["--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"], proxy = {"server":"http://localhost:8080"})
    context_args = {}
    if device:
        context_args.update(pw.devices[device])
    if geolocation:
        context_args["geolocation"] = geolocation
        context_args["permissions"] = ["geolocation"]
    context = browser.new_context(**context_args)
    page = context.new_page()
    return browser, context, page


def login_user(page, email, first_name="John", last_name="Doe"):
    """
    Log into the Expensify app.
    """
    # Open the Expensify app
    page.goto(EXPENSIFY_URL)
    # Login user
    page.get_by_test_id("username").fill(email)
    page.get_by_role("button", name="Continue").click()
    # Check if OTP is required for the login
    try:
        expect(page.get_by_test_id("SignInPage").get_by_test_id("validateCode")).to_be_visible(timeout=7000)
    except (AssertionError, TimeoutError):
        # If not required, expect the join button to appear and click the button
        page.get_by_test_id("SignInPage").get_by_role("button", name="Join").click()
    else:
        # Get the OTP and complete verification
        otp_code = "123456"
        page.get_by_test_id("SignInPage").get_by_test_id("validateCode").fill(otp_code)
    # Check if onboarding is required
    try:
        expect(page.get_by_text("What do you want to do today?")).to_be_visible(timeout=10000)
    except (AssertionError, TimeoutError):
        pass
    else:
        # Complete the onboarding
        page.get_by_label("Track and budget expenses").click()
        page.get_by_role("textbox", name="First name").fill(first_name)
        page.get_by_role("textbox", name="Last name").fill(last_name)
        page.get_by_role("button", name="Continue").click()
        # Exit the Concierge chat, if opened by default
        try:
            page.get_by_role("button", name="Back").first.click(timeout=3000)
        except (AssertionError, TimeoutError):
            pass
    # Dismiss the "Get started here!" tool tip, if shown
    try:
        page.get_by_role("button", name="Close").click(timeout=3000)
    except (AssertionError, TimeoutError):
        pass


def test_submit_expense_header_displays_on_reload_after_selecting_waypoint_menu():
    """
    Verify that the Submit expense menu header displays even after reloading.
    """
    with sync_playwright() as pw:
        # Launch the app and login
        email = generate_user_email()
        LOGGER.info("User email: %s", email)
        LOGGER.info("Launch the app in the mobile view")
        browser, context, page = launch_browser(pw, device="Pixel 7")

        # Start tracing
        context.tracing.start(screenshots=True, snapshots=True, sources=True)

        try:
            login_user(page, email)

            # Open the submit expense widget
            LOGGER.info("Start a Submit expense request")
            page.get_by_role("button", name="Start chat (Floating action)").click()
            page.get_by_role("menuitem", name="Submit expense").click()

            # Select distance and click on the start location
            LOGGER.info("Switch to Distance tab and click on the Start location")
            page.get_by_test_id("IOURequestStartPage").get_by_role("button", name="Distance").click()
            page.get_by_role("menuitem", name="Start").click()

            # Reload the page
            LOGGER.info("Reload the page")
            page.reload()

            # Press the back button
            LOGGER.info("Go back")
            page.get_by_label("Back").click()

            # Add delay to make the header visible to the user running the test
            page.wait_for_timeout(2000)

            # Verify that the header is displayed by checking the visibility of menu item in the header
            LOGGER.info("Verify that the Submit expense menu header is still visible")
            for item in ("Manual", "Scan", "Distance"):
                assert_message = f"'{item}' should be visible in the header"
                expect(page.get_by_label(item), assert_message).to_be_visible(timeout=3)
        except Exception as e:
            # Optionally log the exception
            LOGGER.error("Test failed: %s", e)
            raise
        finally:
            # Stop trace and export
            context.tracing.stop()
            trace_path = '/app/expensify/user_tool/output_browser1.zip'
            context.tracing.export(path=trace_path)
            trace_cleaner(trace_path)

            # Cleanup
            context.close()
            browser.close()
