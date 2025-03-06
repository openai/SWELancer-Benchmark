"""
Test for the issue: https://github.com/Expensify/App/issues/53382
"""

from playwright.sync_api import TimeoutError, expect, sync_playwright

# Expensify app URL
EXPENSIFY_URL = "https://dev.new.expensify.com:8082/"

# Email login credentials
EMAIL_USERNAME = "expensifytesting1@gmail.com"
EMAIL_PASSWORD = "redx tbmr hzpc rbzr"

# Email username postfix
EMAIL_USERNAME_POSTFIX = "53382.6"


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
        page.get_by_label("Manage my team's expenses").click()
        page.get_by_role("button", name="More than 1,000 employees").click()
        page.get_by_role("button", name="Continue").first.click()
        page.get_by_role("button", name="None of the above").first.click()
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


def test_allow_disabling_auto_renew_freely():
    """
    Verify allow disabling auto renew freely if you haven't been billed at least once.
    """
    with sync_playwright() as pw:
        # Login user
        user_email = generate_user_email()
        browser, context, page = launch_browser(pw)
        login_user(page, user_email)

        # Go to Settings -> Subscription
        page.get_by_test_id("CustomBottomTabNavigator").get_by_role("button", name="My settings").click()
        page.get_by_test_id("InitialSettingsPage").get_by_role("menuitem", name="Subscription").click()

        # Enable auto-renew toggle, if disabled
        auto_renew = page.get_by_test_id("SubscriptionSettingsPage").get_by_label("Auto-renew").first
        if not auto_renew.is_checked():
            auto_renew.click()

        # Disable auto-renew toggle, verify that the survey form does not appear, and auto-renew is disabled
        auto_renew.click()
        expect(
            page.get_by_test_id("DisableAutoRenewSurveyPage"),
            "Survey form must not be shown",
        ).not_to_be_visible(timeout=3000)
        expect(
            auto_renew,
            "Auto-renew toggle must be disabled",
        ).not_to_be_checked(timeout=3000)

        # Cleanup
        context.close()
        browser.close()


if __name__ == "__main__":
    test_allow_disabling_auto_renew_freely()
