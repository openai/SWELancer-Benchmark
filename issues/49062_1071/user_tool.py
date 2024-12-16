import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from utils.trace_cleaner import trace_cleaner

"""
Test whether the following console warning disappears on self-dm page: Function components cannot be given refs.
"""
import os
import pytest
from utils.login import sign_up, complete_onboarding
from utils.browser import start_browser, close_browser
from playwright.async_api import expect

# Constants
EXPENSIFY_USERNAME_FIRSTNAME = "osaidtest"
EXPENSIFY_USERNAME_LASTNAME = "testaccount"
EXPENSIFY_USERNAME = f"{EXPENSIFY_USERNAME_FIRSTNAME} {EXPENSIFY_USERNAME_LASTNAME}"
EXPENSIFY_EMAIL_USERNAME = "osaidtest5"
EXPENSIFY_EMAIL = "osaidtest5@gmail.com"
NEW_DOT_URL = "https://dev.new.expensify.com:8082"
OLD_DOT_URL = "http://localhost:9000/"
EXPENSIFY_PASSWORD = "ntvd acej mmaa qqmd"
DATA_DIR = 'browser_context'

EXPENSIFY_DERIVED_EMAIL = "osaidtest5+49062_7@gmail.com"

async def get_user_email(page):
    """
    Get User Email.
    """
    return await page.evaluate(
        """async () => {
        const credentials = await Onyx.get('credentials');
        const {login} = credentials; 
        return login
    }"""
    )

console_warning_detected = False

def track_console_warning(msg):
    if msg.type == 'error' and "Warning: Function components cannot be given refs. Attempts to access this ref will fail." in msg.text:
        global console_warning_detected 
        console_warning_detected = True

async def open_self_dm_page(page, email):
    await page.get_by_label("Start chat (Floating action)").click()
    await page.get_by_text("Start chat").click()
    await page.get_by_test_id("selection-list-text-input").fill(email)
    try:
        await page.get_by_label(f"{EXPENSIFY_USERNAME} (you)").filter(has_text=email).click()
    except:
        await page.get_by_label(EXPENSIFY_DERIVED_EMAIL).click()

@pytest.mark.asyncio
async def test_console_warning_for_function_components_cannot_be_given_refs_should_not_appear_in_self_dm(): 

    # Set up the email to use for the test
    derived_email = EXPENSIFY_DERIVED_EMAIL

    # Start browser
    context, page, playwright = await start_browser(
        persistent=False,
        data_dir=DATA_DIR,
        launch_args=["--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"]
    )

    # Start Playwright trace
    await context.tracing.start(screenshots=True, snapshots=True, sources=True)
    try:
        page.on("console", track_console_warning)
        await sign_up(page, derived_email)
        try:
            await complete_onboarding(page, first_name=EXPENSIFY_USERNAME_FIRSTNAME, last_name=EXPENSIFY_USERNAME_LASTNAME)
        except:
            pass

        # Open Self-DM page.
        await open_self_dm_page(page, derived_email)

        # Validate the absence of the console warning.
        assert not console_warning_detected, "Console Warning 'Function components cannot be given refs' appears in self-dm."

    finally:
        # Stop trace and clean up
        await context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
        trace_cleaner("/app/expensify/user_tool/output_browser1.zip")

        # Close browser
        await close_browser(context, page, playwright)
