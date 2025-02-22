import pytest
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page
from utils.trace_cleaner import trace_cleaner

EMAIL_USERNAME = "ibukunsamuel999"
EMAIL_PASSWORD = "jkgz unyn rnwl slrp"

EXPENSIFY_URL = "https://dev.new.expensify.com:8082/"


def login_user(page, email, first_name="Test", last_name="User"):
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
        expect(page.get_by_test_id("SignInPage").get_by_test_id("validateCode")).to_be_visible()
    except (AssertionError, TimeoutError):
        # If not required, expect the join button to appear and click the button
        page.get_by_test_id("SignInPage").get_by_role("button", name="Join").click()
    # Check if onboarding is required
    try:
        expect(page.get_by_text("What do you want to do today?")).to_be_visible()
    except (AssertionError, TimeoutError):
        pass
    else:
        # Complete the onboarding
        page.get_by_label("Track and budget expenses").click()
        page.get_by_role("textbox", name="First name").fill(first_name)
        page.get_by_role("textbox", name="Last name").fill(last_name)
        page.get_by_role("button", name="Continue").click()
        
    # Expect the main screen to appear
    expect(page.get_by_test_id("BaseSidebarScreen")).to_be_visible()
        
        
# Test to verify that the expense report header appears instantly in 1:1 DM

def test_toggle_delay_submission():
    with sync_playwright() as p:
        # Launch Chromium browser in visible mode (non-headless)
        browser = p.chromium.launch(proxy={"server": "http://localhost:8080"}, headless=False, args=["--no-sandbox", "--disable-dev-shm-usage", "--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"], slow_mo=1000, channel="chromium")
        context = browser.new_context(ignore_https_errors=True)
        # Start tracing
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        page = context.new_page()
        try:
            user_email = 'ibukunsamuel999+1739892705@gmail.com'
            # Step 1: Login User A
            login_user(page, user_email, first_name="Milan", last_name="T")

            if page.get_by_label("Close").count() > 0:
                page.get_by_label("Close").click()

            # Step 2: Click on + icon and click on "New workspace"
            page.get_by_label("My settings").click()

            if page.get_by_label("Close").count() > 0:
                page.get_by_label("Close").click()
            
            page.locator("div[aria-label='Workspaces']").click()
            new_workspace_button = page.get_by_label("New workspace")
            new_workspace_button.click()
            
            # Step 3: Click on More Features
            page_feature = page.locator('div[aria-label="More features"]')
            page_feature.click()       
            
            # Step 4: Enable Workflows Toggle and click on it
            workflows = page.locator('button[aria-label="Configure how spend is approved and paid."]')
            workflows.click()
                   
            workflow_setting = page.locator('div[aria-label="Workflows"]')
            workflow_setting.click()

            # Enable Approvals
            approval_toggle = page.locator('button[aria-label="Require additional approval before authorizing a payment."][role="switch"]')
            if approval_toggle.get_attribute('aria-checked') == "false":
                approval_toggle.click()

            # Modify Approvals
            page.locator('button[aria-label="Add approvals"]').click()
            page.locator(
                'div[data-tag="pressable"]', has_text="Additional Approver"
            ).click()

            # Upgrade Account
            page.locator("button", has_text="Upgrade").click()
            
            
            # Step 7: check if delay submission toggle is off
            is_delay_toggle_off = page.locator("button[aria-label*='Choose a custom schedule']")
            aria_checked_value = is_delay_toggle_off.get_attribute('aria-checked')
            if aria_checked_value == "true":
                assert False, "Delay submissions turns on after upgrading workspace"
            else:
                assert True, "Delay submissions does not turns on after upgrading workspace"
        finally:
            # Stop tracing, export the trace, call trace_cleaner and close the browser
            trace_file = "/app/expensify/user_tool/output_browser1.zip"
            context.tracing.stop(path=trace_file)
            trace_cleaner(trace_file)
            browser.close()