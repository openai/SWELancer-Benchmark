"""
Test for the issue: https://github.com/Expensify/App/issues/53565
"""

from playwright.sync_api import TimeoutError, expect, sync_playwright

# Expensify app URL
EXPENSIFY_URL = "https://dev.new.expensify.com:8082/"

# Email login credentials
EMAIL_USERNAME = "expensifytesting1@gmail.com"
EMAIL_PASSWORD = "redx tbmr hzpc rbzr"

# Email username postfix
EMAIL_USERNAME_POSTFIX = "53565.1"


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
        proxy={"server": "http://localhost:8080"},
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
    # Close the info message if appears
    try:
        page.get_by_role("button", name="Close").click(timeout=2000)
    except (AssertionError, TimeoutError):
        pass


def test_initial_value_field_name():
    """
    Verify that the initial-value field name is not changed.
    """
    with sync_playwright() as pw:
        # Login user
        user_email = generate_user_email()
        browser, context, page = launch_browser(pw)
        login_user(page, user_email)

        # Go to settings
        page.get_by_role("button", name="My settings").click()

        # Create a workspace, if not already created
        page.get_by_test_id("InitialSettingsPage").get_by_role("menuitem", name="Workspaces", exact=True).click()
        texts = page.get_by_test_id("WorkspacesListPage").get_by_label("row").all_inner_texts()
        if not texts:
            page.get_by_test_id("WorkspacesListPage").get_by_role("button", name="New workspace").first.click()
        else:
            page.get_by_test_id("WorkspacesListPage").get_by_label("row").first.click()

        # Enable report fields, if not already done
        page.get_by_test_id("WorkspaceInitialPage").get_by_role("menuitem", name="More features").click()
        ws_report_fields = page.get_by_test_id("WorkspaceMoreFeaturesPage").get_by_label("Set up custom fields")
        if not ws_report_fields.is_checked():
            ws_report_fields.click()
            upgrade = page.get_by_test_id("workspaceUpgradePage").get_by_role("button", name="Upgrade").first
            if upgrade.is_visible():
                upgrade.click()
                page.get_by_test_id("workspaceUpgradePage").get_by_role("button", name="Got it").first.click()

        # Create a report field, if not already created
        field_name = "test-field-53565"
        page.get_by_test_id("WorkspaceInitialPage").get_by_role("menuitem", name="Report fields").click()
        report_field = page.get_by_test_id("WorkspaceReportFieldsPage").get_by_role("button", name=field_name).first
        if not report_field.is_visible():
            page.get_by_test_id("WorkspaceReportFieldsPage").get_by_role("button", name="Add field").click()
            page.get_by_test_id("CreateReportFieldsPage").get_by_role("menuitem", name="Name").click()
            page.get_by_test_id("TextSelectorModal").get_by_role("textbox").fill(field_name)
            page.get_by_test_id("TextSelectorModal").get_by_role("button", name="Save").click()
            page.get_by_test_id("CreateReportFieldsPage").get_by_role("menuitem", name="Type").click()
            page.get_by_test_id("TypeSelectorModal").get_by_role("button", name="Text").click()
            page.get_by_test_id("CreateReportFieldsPage").get_by_role("button", name="Save").click()

        # Open the report field and verify that the initial value menu option is present
        report_field.click()
        expect(
            page.get_by_test_id("ReportFieldsSettingsPage").get_by_role("menuitem", name="Initial value"),
            "'Initial value' menu option must be shown in the report field settings",
        ).to_be_visible(timeout=2000)

        # Cleanup
        context.close()
        browser.close()


if __name__ == "__main__":
    test_initial_value_field_name()
