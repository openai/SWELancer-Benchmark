import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, Page
from utils.trace_cleaner import trace_cleaner

# Define the function to log in using the retrieved magic code
def login_user(page: Page):
    page.goto("http://localhost:8082/")
    page.wait_for_load_state("networkidle")
    page.locator("input[name='username']").click()
    # Fill the input field with the desired text
    page.locator("input[name='username']").fill("usama.shahid1255198@gmail.com")

    page.locator("input[name='username']").press("Enter")
    page.wait_for_timeout(2000)
    magic_code = '123456'
    page.wait_for_timeout(2000)
    for i, digit in enumerate(magic_code):
      selector = f"div:nth-child({i + 1}) > div:nth-child(2) > div > div > div > .css-view-175oi2r > .css-textinput-11aywtz"
      page.locator(selector).fill(digit)
    page.wait_for_timeout(2000)

# Define the main test function
def test_app_crash_on_wallet():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            proxy = {"server": "http://127.0.0.1:8080/"},
            args=[
                "--ignore-certificate-errors",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process"
            ]
        )
        context = browser.new_context()

        # Start tracing
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        page = context.new_page()
        console_errors = []

        try:
            # Perform login
            login_user(page)
            page.wait_for_timeout(2000)
            page.locator("[data-testid='SvgDefaultAvatar8 Icon']").first.wait_for(state="visible")
            page.wait_for_timeout(2000)
            page.locator("[data-testid='SvgDefaultAvatar8 Icon']").nth(0).click()
            page.wait_for_timeout(2000)
            wallet_element = page.locator("div[aria-label='Wallet'][role='menuitem']")

            # Listen for console messages and store errors
            context.on("console", lambda msg: console_errors.append(msg.text))
            page.wait_for_timeout(2000)
            wallet_element.click()
            page.wait_for_timeout(2000)
            assert not any(
                "Invalid value for prop" in error and "data-testid" in error and "ScreenWrapper" in error
                for error in console_errors
            ), "Test failed: Invalid value for prop `data-testid` on <div> tag. Either remove it from the element, or pass a string or number value to keep it in the DOM"

            print("Test passed: No invalid prop value error found in console logs.")
        except Exception as e:
            print("Test encountered an exception:", e)
            raise
        finally:
            # Stop tracing and clean the trace
            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            context.tracing.stop(path=trace_path)
            trace_cleaner(trace_path)

        context.close()
        browser.close()
