from playwright.sync_api import sync_playwright
from utils.trace_cleaner import trace_cleaner


# Expensify app URL
EXPENSIFY_URL = "https://dev.new.expensify.com:8082/"

# Email login credentials
EMAIL_USERNAME = "naturesv057+54767_1@gmail.com"

def launch_browser(pw, device=None, geolocation=None):
    """
    Launch the browser.
    """
    browser = pw.chromium.launch(
        headless=False,
        proxy={"server": "http://127.0.0.1:8080/"},
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
    
    # Get the OTP code
    otp = "123456"
    
    # Enter the OTP code
    page.keyboard.type(otp)


def test_54767():
    with sync_playwright() as p:
        browser, context, page = launch_browser(p)
        # Start tracing with screenshots, snapshots and sources
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        try:
            # Step 1: Login user
            login_user(page)
            page.wait_for_timeout(2000)

            # Connect to Chrome DevTools Protocol (CDP)
            session = context.new_cdp_session(page)

            # Set CPU Throttling
            session.send("Emulation.setCPUThrottlingRate", {"rate": 6})  # 6x CPU slowdown

            # Set Network Throttling (Slow 3G)
            session.send("Network.emulateNetworkConditions", {
                "offline": False,
                "latency": 400,  # 400ms (Slow 3G)
                "downloadThroughput": 400 * 1024,  # 400 kbps
                "uploadThroughput": 150 * 1024   # 150 kbps
            })

            # Step 2: Reintroduce scenario
            page.get_by_label("My settings").click()
            page.get_by_label("Wallet").click()
            page.wait_for_timeout(2000)
            page.locator("body").press("ControlOrMeta+d")
            page.wait_for_timeout(2000)
            page.get_by_label("Force offline").click()
            page.wait_for_timeout(2000)

            # Step 3: Check if the issue is resolved
            button = page.locator("button[aria-label='Force offline']")  # Locate the button
            aria_checked = button.get_attribute("aria-checked")  # Get the value of aria-checked
            assert aria_checked == "true", f"aria-checked is {aria_checked}, expected 'true'"
        finally:
            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            # Stop tracing and export the trace file
            context.tracing.stop(path=trace_path)
            # Clean the trace file using trace_cleaner
            trace_cleaner(trace_path)
            # Close the browser
            browser.close()


if __name__ == '__main__':
    test_54767()