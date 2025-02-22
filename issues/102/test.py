"""
Test for the issue: https://github.com/Expensify/App/issues/52678
"""

from playwright.sync_api import TimeoutError, expect, sync_playwright

# Expensify app URL
EXPENSIFY_URL = "https://dev.new.expensify.com:8082/"

# Email login credentials
EMAIL_USERNAME = "expensifytesting1@gmail.com"
EMAIL_PASSWORD = "redx tbmr hzpc rbzr"

# Email username postfix
EMAIL_USERNAME_POSTFIX = "52678.4"


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
        headless=False,
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


def test_approver_field_in_tag_editor_shows_user_name():
    """
    Verify that the approver field in the tag editor shows the user name instead of user email.
    """
    with sync_playwright() as pw:
        # Login user
        user_email = generate_user_email()
        fname, lname = "John", "Doe"
        user_name = " ".join([fname, lname]).strip()
        browser, context, page = launch_browser(pw)
        login_user(page, user_email, first_name=fname, last_name=lname)

        # Create a new workspace, if one is not already created
        page.get_by_role("button", name="My settings").click()
        page.get_by_test_id("InitialSettingsPage").get_by_role("menuitem", name="Workspaces", exact=True).click()
        texts = page.get_by_test_id("WorkspacesListPage").get_by_label("row").all_inner_texts()
        if not texts:
            page.get_by_test_id("WorkspacesListPage").get_by_role("button", name="New workspace").first.click()
        else:
            page.get_by_test_id("WorkspacesListPage").get_by_label("row").first.click()

        # Enable workflows, rules, and tags, if not already enabled
        page.get_by_test_id("WorkspaceInitialPage").get_by_role("menuitem", name="More features").click()
        ws_workflows = page.get_by_test_id("WorkspaceMoreFeaturesPage").get_by_label("Configure how spend is approved")
        if not ws_workflows.is_checked():
            ws_workflows.click()
        ws_rules = page.get_by_test_id("WorkspaceMoreFeaturesPage").get_by_label("Require receipts, flag high spend")
        if not ws_rules.is_checked():
            ws_rules.click()
            if page.get_by_test_id("workspaceUpgradePage").is_visible():
                page.get_by_test_id("workspaceUpgradePage").get_by_role("button", name="Upgrade").click()
                page.get_by_test_id("workspaceUpgradePage").get_by_role("button", name="Got it").click()
        ws_tags = page.get_by_test_id("WorkspaceMoreFeaturesPage").get_by_label("Classify costs and track billable")
        if not ws_tags.is_checked():
            ws_tags.click()

        # Enable approvals, if not already enabled
        page.get_by_test_id("WorkspaceInitialPage").get_by_role("menuitem", name="Workflows").click()
        ws_approvals = page.get_by_test_id("WorkspacePageWithSections").get_by_label("Require additional approval")
        if not ws_approvals.is_checked():
            ws_approvals.click()

        # Delete, if the tag already exists
        tag_name = "Tag 1"
        page.get_by_test_id("WorkspaceInitialPage").get_by_role("menuitem", name="Tags").click()
        tag = page.get_by_test_id("WorkspaceTagsPage").get_by_role("button", name=tag_name).first
        if tag.is_visible():
            tag.click()
            page.get_by_test_id("TagSettingsPage").get_by_role("menuitem", name="Delete").click()
            page.get_by_role("button", name="Delete").click()

        # Create tag
        page.get_by_test_id("WorkspaceTagsPage").get_by_role("button", name="Add tag").click()
        page.get_by_test_id("CreateTagPage").get_by_role("textbox", name="Name").fill(tag_name)
        page.get_by_test_id("CreateTagPage").get_by_role("button", name="Save").click()

        # Assign approver to the tag
        tag.click()
        page.get_by_test_id("TagSettingsPage").get_by_text("Approver").click()
        page.get_by_test_id("TagApproverPage").get_by_role("button", name=user_name).click()

        # Verify approver field in tag editor shows user name
        expect(
            page.get_by_test_id("TagSettingsPage").get_by_role("menuitem", name=user_name),
            "User name should be visible in the approver field",
        ).to_be_visible(timeout=2000)

        # Cleanup
        context.close()
        browser.close()


if __name__ == "__main__":
    test_approver_field_in_tag_editor_shows_user_name()
