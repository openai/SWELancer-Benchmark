from playwright.sync_api import sync_playwright, expect


# Expensify app URL
EXPENSIFY_URL = "https://dev.new.expensify.com:8082/"

# Email login credentials
EMAIL_USERNAME = "naturesv057+52030_1@gmail.com"

def launch_browser(pw, device=None, geolocation=None):
    """
    Launch the browser.
    """
    browser = pw.chromium.launch(
        headless=False,
        proxy = {"server": "http://127.0.0.1:8080/"},
        args=[
            "--ignore-certificate-errors",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
        ],
        slow_mo=500
    )
    context_args = {}
    if device:
        context_args.update(pw.devices[device])
    if geolocation:
        context_args["geolocation"] = geolocation
        context_args["permissions"] = ["geolocation"]
    context = browser.new_context(**context_args)
    page = context.new_page()
    return browser, context, page


def login_user(page):
    """
    Login to the Expensify app and complete the onboarding.
    """
    # Open the Expensify app
    page.goto(EXPENSIFY_URL)

    # Login user
    page.get_by_role("textbox", name="Phone or email").fill(EMAIL_USERNAME)
    page.locator("div", has_text="Continue").last.click()
    
    # Get the OTP code from the email
    otp = "123456"
    
    # Enter the OTP code
    page.keyboard.type(otp)


def test_52030():
    with sync_playwright() as p:
        # Step 1: Login user
        browser, context, page = launch_browser(p)
        login_user(page)
        page.wait_for_timeout(5000)

        # Step 2: Reintroduce scenario
        try:
            page.get_by_label("Workspaces").click(timeout=2000)
        except:
            page.get_by_label("Track and budget expenses").click()
            page.get_by_role("textbox", name="First name").fill("John")
            page.get_by_role("textbox", name="Last name").fill("Doe")
            page.get_by_role("button", name="Continue").click()
            page.get_by_label("Workspaces").click()

        #Step 3: Check if the issue is resolved
        expect(page.get_by_label("New workspace")).not_to_be_visible()
