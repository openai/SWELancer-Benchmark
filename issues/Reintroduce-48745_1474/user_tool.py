import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

"""\nVerify that the 'Number of Employees' Page and 'Account Package' are successfully implemented with all the given options.\n\n"""

import os
import pytest
from playwright.async_api import expect
from utils.login import sign_up 
from utils.email_handler import get_unique_derived_email
from utils.browser import start_browser, close_browser

# Added import for the trace cleaner
from utils.trace_cleaner import trace_cleaner

# Constants
EXPENSIFY_USERNAME_FIRSTNAME = "osaidtest"
EXPENSIFY_USERNAME_LASTNAME = "testaccount"
EXPENSIFY_USERNAME = f"{EXPENSIFY_USERNAME_FIRSTNAME} {EXPENSIFY_USERNAME_LASTNAME}"
EXPENSIFY_EMAIL_USERNAME = "osaidtest5"
EXPENSIFY_EMAIL = "osaidtest5@gmail.com"
NEW_DOT_URL = "https://dev.new.expensify.com:8082"
OLD_DOT_URL = "http://localhost:9000/"
EXPENSIFY_PASSWORD = "ntvd acej mmaa qqmd"
DATA_DIR = "browser_context"
UNIQUE_EXPENSIFY_EMAIL = "osaidtest5+dd48745_1234@gmail.com"

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


async def enable_onboarding_for_existing_user(page):
    """
    Re-enable onboarding setup for persisted and logged in user.
    """
    return await page.evaluate(
        """async () => {
        await Promise.all([Onyx.set("nvp_onboarding", {hasCompletedGuidedSetupFlow: false}), Onyx.set("onboardingLastVisitedPath", "/onboarding/purpose") ]);
    }"""
    )

@pytest.mark.asyncio
async def test_new_onboarding_workflow_pages():
    trace_path = "/app/expensify/user_tool/output_browser1.zip"

    # Start browser
    context, page, playwright = await start_browser(
        persistent=False, 
        data_dir=DATA_DIR, 
        launch_args=[
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ]
    )

    # Begin trace recording
    await context.tracing.start(
        screenshots=True,
        snapshots=True
    )

    try:
        # Set up the email to use for the test
        derived_email = UNIQUE_EXPENSIFY_EMAIL
        await sign_up(page, derived_email)

        await page.wait_for_timeout(3000)
        await page.get_by_text("Manage my team's expenses").click()

        # Assert that 'Number of Employees' page is properly implemented.
        await expect(page.get_by_label("1-10 employees")).to_be_visible()
        await expect(page.get_by_label("11-50 employees")).to_be_visible()
        await expect(page.get_by_label("51-100 employees")).to_be_visible()
        await expect(page.get_by_label("101-1,000 employees")).to_be_visible()
        await expect(page.get_by_label("More than 1,000 employees")).to_be_visible()

        # Go to 'Accounting Package' Page
        await page.get_by_label("More than 1,000 employees").click()

        await page.wait_for_timeout(2000)
        await page.get_by_role("button", name="Continue").click()

        await page.wait_for_timeout(2000)
        # Assert that 'Account Package' Page is properly implemented.
        await expect(page.get_by_label("Quickbooks Online")).to_be_visible()
        await expect(page.get_by_label("Xero")).to_be_visible()
        await expect(page.get_by_label("NetSuite")).to_be_visible()
        await expect(page.get_by_label("Sage Intacct")).to_be_visible()
        await expect(page.get_by_label("None of the above")).to_be_visible()

        # Close Onboarding workflow.
        await page.get_by_label("None of the above").click()
        await page.get_by_test_id("BaseOnboardingAccounting").get_by_role(
            "button", name="Continue"
        ).click()

    finally:
        # Stop the trace and save it, then clean it.
        await context.tracing.stop(path=trace_path)
        trace_cleaner(trace_path)
        # Close browser
        await close_browser(context, page, playwright)
