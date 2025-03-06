'''
Test for the issue: https://github.com/Expensify/App/issues/52904
'''

from playwright.sync_api import TimeoutError, expect, sync_playwright
from utils.trace_cleaner import trace_cleaner

# Expensify app URL
EXPENSIFY_URL = "https://dev.new.expensify.com:8082/"

# Email login credentials
EMAIL_USERNAME = "expensifytesting1@gmail.com"
EMAIL_PASSWORD = ""

# Email username postfix
EMAIL_USERNAME_POSTFIX = "52904.3"


def generate_user_email(user_id=None):
    """
    Generate an email address for user login.
    """
    temp = EMAIL_USERNAME.rsplit("@", 1)
    username = temp[0].strip()
    domain = temp[1].strip()
    return f"{username}+{EMAIL_USERNAME_POSTFIX}{user_id or ''}@{domain}"


def launch_browser(pw, headless=False, device=None, permissions=None, geolocation=None):
    """
    Launch the browser.
    """
    browser = pw.chromium.launch(
        channel="chrome",
        headless=headless,
        args=[
            "--ignore-certificate-errors",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
        ],
        slow_mo=1000,
    )
    context_args = {"permissions": permissions or []}
    if device:
        context_args.update(pw.devices[device])
    if geolocation:
        context_args["geolocation"] = geolocation
        context_args["permissions"].append("geolocation")
    context = browser.new_context(**context_args)
    page = context.new_page()
    return browser, context, page


def login_user(page, user_email, first_name="John", last_name="Doe"):
    """
    Log into the Expensify app.
    """
    # Open the Expensify app
    page.goto(EXPENSIFY_URL)
    # Login user
    page.get_by_test_id("username").fill(user_email)
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
        try:
            page.get_by_test_id("SignInPage").get_by_role("button", name="Sign in").click(timeout=2000)
        except (AssertionError, TimeoutError):
            pass
    # Check if onboarding is required
    try:
        expect(page.get_by_text("What do you want to do today?")).to_be_visible(timeout=5000)
    except (AssertionError, TimeoutError):
        pass
    else:
        # Complete the onboarding
        page.get_by_label("Track and budget expenses").click()
        page.get_by_role("button", name="Continue").first.click()
        page.get_by_role("textbox", name="First name").fill(first_name)
        page.get_by_role("textbox", name="Last name").fill(last_name)
        page.get_by_role("button", name="Continue").last.click()
    # Dismiss get started dialog if appears
    try:
        page.get_by_role("button", name="Get started").click(timeout=3000)
    except (AssertionError, TimeoutError):
        pass
    # Expect the main screen to appear
    expect(page.get_by_test_id("BaseSidebarScreen")).to_be_visible(timeout=7000)


def test_navigating_back_from_the_access_level_page():
    """
    Verify that the app navigates to the confirmation page on navigating back from access level page.
    """
    with sync_playwright() as pw:
        # Login user
        user_email = generate_user_email()
        browser, context, page = launch_browser(pw)
        # Start tracing
        context.tracing.start(screenshots=True, snapshots=True, sources=True)

        try:
            login_user(page, user_email)

            # Go to Settings -> Security
            page.get_by_test_id("CustomBottomTabNavigator").get_by_role("button", name="My Settings").click()
            page.get_by_test_id("InitialSettingsPage").get_by_role("menuitem", name="Security").click()

            # Add copilot
            other_user_email = "otheruser@gmail.com"
            page.get_by_test_id("SettingSecurityPage").get_by_role("menuitem", name="Add copilot").click()
            page.get_by_test_id("AddDelegatePage").get_by_role("textbox", name="Name, email, or phone number").fill(other_user_email)
            page.get_by_test_id("AddDelegatePage").get_by_text(other_user_email).last.click()
            page.get_by_test_id("SelectDelegateRolePage").get_by_role("button", name="Full").click()
            page.get_by_test_id("ConfirmDelegatePage").get_by_role("menuitem", name="Full").click()

            # Verify navigation
            page.get_by_test_id("SelectDelegateRolePage").get_by_role("button", name="Back").click()
            expect(
                page.get_by_test_id("ConfirmDelegatePage"),
                "Confirmation page should appear on navigating back from access level page",
            ).to_be_visible(timeout=2000)

        finally:
            # Stop tracing and export trace file
            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            context.tracing.stop(path=trace_path)
            trace_cleaner(trace_path)
            context.close()
            browser.close()


if __name__ == "__main__":
    test_navigating_back_from_the_access_level_page()