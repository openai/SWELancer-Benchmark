"""
Test for the issue: https://github.com/Expensify/App/issues/53694
"""

from playwright.sync_api import TimeoutError, expect, sync_playwright

# Expensify app URL
EXPENSIFY_URL = "https://dev.new.expensify.com:8082/"

# Email login credentials
EMAIL_USERNAME = "expensifytesting1@gmail.com"
EMAIL_PASSWORD = "redx tbmr hzpc rbzr"

# Email username postfix
EMAIL_USERNAME_POSTFIX = "53694.7"


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


def test_invoice_title_changes_after_renaming():
    """
    Verify that the invoice title changes after renaming.
    """
    with sync_playwright() as pw:
        # Login user
        user_email = generate_user_email()
        browser, context, page = launch_browser(pw)
        login_user(page, user_email)

        # Login other user
        other_user_email = generate_user_email(user_id="other")
        # browser1, context1, page1 = launch_browser(pw)
        # login_user(page1, other_user_email, first_name="Other", last_name="User")

        # Create a new workspace, if one is not already created
        page.get_by_role("button", name="My settings").click()
        # Close the info message if appears
        try:
            page.get_by_role("button", name="Close").click(timeout=2000)
        except (AssertionError, TimeoutError):
            pass
        page.get_by_test_id("InitialSettingsPage").get_by_role("menuitem", name="Workspaces", exact=True).click()
        texts = page.get_by_test_id("WorkspacesListPage").get_by_label("row").all_inner_texts()
        if not texts:
            page.get_by_test_id("WorkspacesListPage").get_by_role("button", name="New workspace").first.click()
        else:
            page.get_by_test_id("WorkspacesListPage").get_by_label("row").first.click()

        # Enable invoices, if not already enabled
        page.get_by_test_id("WorkspaceInitialPage").get_by_role("menuitem", name="More features").click()
        invoices = page.get_by_test_id("WorkspaceMoreFeaturesPage").get_by_label("Send and receive invoices")
        if not invoices.is_checked():
            invoices.click()
        page.get_by_test_id("WorkspaceInitialPage").get_by_role("button", name="Back").click()

        # Send invoice
        company_name = "My Company"
        company_website = "https://www.psbloansin59minutes.com/home"
        page.get_by_role("button", name="Inbox").click()
        page.get_by_role("button", name="Start chat (Floating action)").click()
        page.get_by_role("menuitem", name="Send invoice").click()
        page.get_by_test_id("IOURequestStartPage").get_by_role("textbox").fill("5")
        page.get_by_test_id("IOURequestStartPage").get_by_role("button", name="Next").click()
        page.get_by_test_id("IOURequestStepParticipants").get_by_role("textbox").fill(other_user_email)
        page.get_by_test_id("IOURequestStepParticipants").get_by_text(other_user_email).last.click()
        try:
            # Send button would appear on the confirmation page if the company info is already filled in the past
            expect(
                page.get_by_test_id("IOURequestStepConfirmation").get_by_role("button", name="Send", exact=False)
            ).to_be_visible(timeout=2000)
        except (AssertionError, TimeoutError):
            page.get_by_test_id("IOURequestStepConfirmation").get_by_role("button", name="Next").click()
            page.get_by_test_id("IOURequestStepCompanyInfo").get_by_role("textbox", name="Your company name").fill(
                company_name
            )
            page.get_by_test_id("IOURequestStepCompanyInfo").get_by_role("textbox", name="Your company website").fill(
                company_website
            )
            page.get_by_test_id("IOURequestStepCompanyInfo").get_by_role("button", name="Send", exact=False).click()
        else:
            page.get_by_test_id("IOURequestStepConfirmation").get_by_role("button", name="Send", exact=False).click()

        # Edit invoice title
        new_title = "New Invoice Title"
        page.get_by_test_id("report-actions-view-wrapper").get_by_label("Chat message").get_by_role(
            "button", name="View details"
        ).first.click()
        try:
            page.get_by_role("button", name="Invoice ", exact=False).first.click(timeout=10000)
        except (AssertionError, TimeoutError):
            # To handle the broken state
            page.get_by_role("button", name=" owes  ", exact=False).first.click(timeout=2000)
        page.get_by_test_id("ReportDetailsPage").get_by_text("Title").click()
        page.get_by_test_id("EditReportFieldPage").get_by_role("textbox").fill(new_title)
        page.get_by_test_id("EditReportFieldPage").get_by_role("button", name="Save").click()

        # Verify invoice is renamed
        expect(
            page.get_by_test_id("ReportDetailsPage").get_by_role("menuitem", name=new_title),
            "Invoice title should change after renaming",
        ).to_be_visible(timeout=3000)

        # Cleanup
        context.close()
        browser.close()


if __name__ == "__main__":
    test_invoice_title_changes_after_renaming()
