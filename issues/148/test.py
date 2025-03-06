from playwright.sync_api import sync_playwright


# Expensify app URL
EXPENSIFY_URL = "https://dev.new.expensify.com:8082/"

# Email login credentials
EMAIL_USERNAME = "naturesv057+51982_2@gmail.com"

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
    page.wait_for_timeout(2000)
    
    # Get the OTP code from the email
    otp = "123456"
    
    # Enter the OTP code
    page.keyboard.type(otp)


def test_51982():
    with sync_playwright() as p:
        # Step 1: Login user
        browser, context, page = launch_browser(p)
        login_user(page)
        page.wait_for_timeout(2000)

        # Step 2: Reintroduce scenario
        page.get_by_label("My settings").click()
        page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()
        page.get_by_label("New workspace").click()
        page.get_by_label("More features").click()
        page.get_by_label("Set up custom fields for").click()
        page.get_by_role("button", name="Upgrade").click()
        page.get_by_role("link", name="View your subscription").click()
        page.go_back()

        #Step 3: Check if the issue is resolved
        g_element = page.locator("svg g[clip-path]").last # Locate the <g> element inside the SVG

        initial_box = g_element.bounding_box() # Get the initial position
        page.wait_for_timeout(1000)

        new_box = g_element.bounding_box()  # Get the position after 1 second

        assert initial_box != new_box, f"SVG image is not animating! Position did not change." # Assert that the <g> element has moved (is animating)
