from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page

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

    if page.get_by_label("Close").count() > 0:
        page.get_by_label("Close").click()
        
    # Expect the main screen to appear
    expect(page.get_by_test_id("BaseSidebarScreen")).to_be_visible()
        
        
# Test to verify that the expense report header appears instantly in 1:1 DM
def test_workspace_non_editable_rows_on_hover():
    with sync_playwright() as p:
         # Launch Chromium browser in visible mode (non-headless)
        browser = p.chromium.launch(headless=False,
                                    args=[
                                    "--ignore-certificate-errors",
                                    "--disable-web-security",
                                    "--disable-features=IsolateOrigins,site-per-process"
                                    ],
                                    slow_mo=1000)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        email1 = 'ibukunsamuel999+1740001955@gmail.com'
        # Step 1: Login User A
        login_user(page, email1, first_name="Test", last_name="User1")

        email2 = 'ibukunsamuel999+1740001975@gmail.com'
        context1 = browser.new_context(ignore_https_errors=True)
        page1 = context1.new_page()
        login_user(page1, email2, first_name="Test", last_name="User2")

        page.get_by_label("My settings").click()
        if page.get_by_label("Close").count() > 0:
            page.get_by_label("Close").click()
        page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()
        page.get_by_label("New workspace").last.click()
        page.get_by_label("Members").click()
        page.get_by_role("button", name="Invite member").click()
        
        page.get_by_test_id("selection-list-text-input").fill(email2)
        page.get_by_label("Test User2").last.click()
        page.get_by_role("button", name="Next").click()
        page.get_by_test_id("WorkspaceInviteMessagePage").get_by_role("button", name="Invite").click()
        
        page1.reload()
        page1.get_by_label("My settings").click()
        if page1.get_by_label("Close").count() > 0:
            page1.get_by_label("Close").click()
        page1.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()
        page1.get_by_text("Test User1's Workspace").last.click()
        non_editable = page1.get_by_role("menuitem", name="NGN - ₦")
        non_editable_initial_bg_color = non_editable.evaluate("element => window.getComputedStyle(element).backgroundColor")

        non_editable.hover()

        non_editable_bg_color = non_editable.evaluate("element => window.getComputedStyle(element).backgroundColor")

        assert non_editable_initial_bg_color == non_editable_bg_color, "Disabled description text Background color changed on hover"

        # ---------------------
        page1.close()
        page.close()
        context1.close()
        context.close()
        browser.close()