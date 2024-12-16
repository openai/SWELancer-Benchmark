import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import Playwright, sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page

EMAIL_USERNAME_1 = "aliceoglualice+41285_10@gmail.com"
EMAIL_USERNAME_2 = "aliceoglualice+41285_11@gmail.com"
EMAIL_PASSWORD = "cfpy ofxm lcmq aeta"

def login_user(p: PlaywrightContextManager, first_name, last_name, user_email) -> tuple[Browser, Page, str]:
    # Launch chromiun and open new page
    browser = p.chromium.launch(headless=True, args=[
        "--disable-web-security",
        "--disable-features=IsolateOrigins,site-per-process",
        "--ignore-certificate-errors"
    ])
    page = browser.new_page()

    # Step 1: Open expensify url
    page.goto('https://dev.new.expensify.com:8082/')

    # Step 2: Enter email and click continue
    page.get_by_test_id("username").fill(user_email)
    page.get_by_role("button", name="Continue").click()
    # Check if OTP is required for the login
    try:
        expect(page.get_by_test_id("SignInPage").get_by_test_id("validateCode")).to_be_visible(timeout=1000)
    except (AssertionError, TimeoutError):
        # If not required, expect the join button to appear and click the button
        page.get_by_test_id("SignInPage").get_by_role("button", name="Join").click()
    else:
        # Get the OTP and complete verification
        otp_code ="123456"
        otp_input = page.locator('input[autocomplete="one-time-code"]')
        otp_input.fill(otp_code)

    # Check if onboarding is required
    try:
        expect(page.get_by_text("What do you want to do today?")).to_be_visible(timeout=5000)
    except (AssertionError, TimeoutError):
        pass
    else:
        # Complete the onboarding
        page.get_by_label("Track and budget expenses").click()
        page.get_by_role("textbox", name="First name").fill(first_name)
        page.get_by_role("textbox", name="Last name").fill(last_name)
        page.get_by_role("button", name="Continue").click()
    
    return browser, page, user_email


def test_merchant_info_field_is_required_appeared():
    from utils.trace_cleaner import trace_cleaner
    with sync_playwright() as p:
        # 1) Login user2 (not traced, just a quick login)
        browser2, _, user_email2 = login_user(p, "Bob", "B", EMAIL_USERNAME_2)
        browser2.close()

        # 2) Now, for user1 and the main steps, record Playwright trace
        trace_path = "/app/expensify/user_tool/output_browser1.zip"
        browser = None
        try:
            # Create a new browser/context and start tracing
            browser = p.chromium.launch(headless=True, args=[
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
                "--ignore-certificate-errors"
            ])
            context = browser.new_context()
            context.tracing.start(screenshots=True, snapshots=True, sources=True)

            # Login user1
            page = context.new_page()
            page.goto('https://dev.new.expensify.com:8082/')
            page.get_by_test_id("username").fill(EMAIL_USERNAME_1)
            page.get_by_role("button", name="Continue").click()
            try:
                expect(page.get_by_test_id("SignInPage").get_by_test_id("validateCode")).to_be_visible(timeout=1000)
            except (AssertionError, TimeoutError):
                page.get_by_test_id("SignInPage").get_by_role("button", name="Join").click()
            else:
                otp_code = "123456"
                otp_input = page.locator('input[autocomplete="one-time-code"]')
                otp_input.fill(otp_code)

            # Check if onboarding is required
            try:
                expect(page.get_by_text("What do you want to do today?")).to_be_visible(timeout=5000)
            except (AssertionError, TimeoutError):
                pass
            else:
                page.get_by_label("Track and budget expenses").click()
                page.get_by_role("textbox", name="First name").fill("Alice")
                page.get_by_role("textbox", name="Last name").fill("A")
                page.get_by_role("button", name="Continue").click()

            # Step 3: Search user2 to send message
            page.get_by_label("Start chat (Floating action)").click()
            page.get_by_text("Start chat").click()
            page.get_by_test_id("selection-list-text-input").fill(user_email2)

            # Step 4: Send message to User2
            page.get_by_label("Bob B").click()
            page.get_by_role("textbox").fill("Hello")
            page.get_by_label("Send").nth(1).click()

            # Step 5: Create new workspace
            page.get_by_label("Start chat (Floating action)").click()
            page.get_by_text("New workspace").click()

            # Step 6: Activate invoices
            page.get_by_text("More features").click()
            page.get_by_label("Send and receive invoices.").click()
            page.get_by_label("Back").click()
            page.locator('div[dir="auto"]:has-text("Alice A\'s Workspace")').click()
            page.get_by_label("Back").click()
            page.wait_for_timeout(1000)

            # Step 7: Send invoices
            page.get_by_label("Start chat (Floating action)").click()
            page.get_by_text("Send invoice").click()
            page.get_by_label("Select a currency").click()
            page.get_by_test_id("selection-list-text-input").fill("TRY")
            page.get_by_label("TRY - TL").click()
            page.get_by_placeholder("0").fill("111")
            page.get_by_role("button", name="Next").click()
            page.get_by_test_id("selection-list").get_by_label("Bob B").click()
            page.get_by_label("Show more").click()
            page.get_by_role("button", name="Next").click()
            page.get_by_role("textbox", name="Your company name").fill("Turing")
            page.get_by_role("textbox", name="Your company website").click()
            page.get_by_role("textbox", name="Your company website").fill("https://turing.com")
            page.get_by_role("button", name="Send TRY 111.00 invoice").click()
            page.get_by_label("View details").click()
            page.get_by_text("Merchant").click()
            page.get_by_role("textbox", name="Merchant").click()
            page.get_by_role("button", name="Save").click()

            # Step 8: Assertion invoices
            element = page.get_by_text("This field is required.")
            assert not element.is_visible(), "The text 'This field is required.' is not visible on the page."

        except Exception as e:
            # Re-raise after the finally block ensures the trace is saved.
            raise e
        finally:
            # Stop trace and clean it, then close browser
            if browser:
                # Because we used a single context here:
                for c in browser.contexts:
                    c.tracing.stop(path=trace_path)
                trace_cleaner(trace_path)
                browser.close()
