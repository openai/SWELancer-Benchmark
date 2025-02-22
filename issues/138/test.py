import re
from playwright.sync_api import sync_playwright


# Expensify app URL
EXPENSIFY_URL = "https://dev.new.expensify.com:8082/"

# Email login credentials
EMAIL_USERNAME = "naturesv057+52198_1@gmail.com"

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


def test_52198():
    with sync_playwright() as p:
        # Step 1: Login user
        browser, context, page = launch_browser(p)
        login_user(page)
        page.wait_for_timeout(5000)

        # Step 2: Reintroduce scenario
        # Define the locators
        locator1 = page.locator("div").filter(has_text=re.compile(r"^\.expensify-app-icon_svg__st1\{fill:#002e22\}DEV/Inbox$")).first
        locator2 = page.get_by_test_id("2721644976521748")

        # Get bounding boxes
        box1 = locator1.bounding_box()
        box2 = locator2.bounding_box()

        # Ensure both elements exist
        assert box1 is not None and box2 is not None, "One or both elements were not found on the page."

        # Calculate space between elements
        bottom_of_locator1 = box1["y"] + box1["height"]
        top_of_locator2 = box2["y"]

        # Compute the gap
        gap = top_of_locator2 - bottom_of_locator1

        # Step 3: Check if the issue is resolved
        assert gap == 12, f"Expected gap to be 12px but found {gap}px." # Assert the gap is exactly 12px
