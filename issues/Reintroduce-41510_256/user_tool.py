import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from playwright._impl._page import Page

PASSWORD = "bruzwjfovckiesys"
NEW_DOT_URL = "https://dev.new.expensify.com:8082"
OLD_DOT_URL = "http://localhost:9000/"
ONE_SECOND = 1000
TWO_SECONDS = 2000
THREE_SECONDS = 3000
FIVE_SECONDS = 5000
EMAIL = "adebayovicktor0+tests41510@gmail.com"

# Sign In to Expensify
def sign_in_new_dot(page: Page, email: str, url: str = None):
    """
    Sign in into the new Expensify dot.
    """
    # Go to URL
    url = url if url else NEW_DOT_URL
    page.goto(url)
    # Sign In
    page.get_by_test_id("username").fill(email)
    page.wait_for_timeout(TWO_SECONDS)
    page.get_by_role("button", name="Continue").click()
    page.wait_for_timeout(FIVE_SECONDS)
    # OTP is hardcoded for replay
    page.wait_for_timeout(FIVE_SECONDS)
    otp = '123456'
    page.get_by_test_id("validateCode").fill(otp)
    page.wait_for_timeout(TWO_SECONDS)

    # Wait sign in to complete
    page.get_by_text("Please enter the magic code").wait_for(state="hidden")
    page.wait_for_timeout(THREE_SECONDS)


def test():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            proxy={"server": "http://127.0.0.1:8080/"},
            args=[
                "--ignore-certificate-errors",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process"
            ],
            slow_mo=500
        )
        context = browser.new_context(ignore_https_errors=True)
        # Start tracing
        context.tracing.start(
            title="trace",
            screenshots=True,
            snapshots=True,
            sources=True
        )

        page: Page = context.new_page()
        try:
            # Sign in
            sign_in_new_dot(page, EMAIL)

            # Click second chat
            second_chat_button = page.locator('[aria-label="Navigates to a chat"]').nth(1)
            second_chat_button.click()
            page.wait_for_timeout(1000)

            # Click Create button
            click_create_button = page.locator('button[aria-label="Create"]').last
            click_create_button.click()
            page.wait_for_timeout(1000)

            # Click assign task
            click_submit_expense_button = page.locator("[aria-label='Assign task']")
            click_submit_expense_button.click()
            page.wait_for_timeout(1000)

            # fill title
            page.locator('input[aria-label="Title"]').fill("title something")
            page.wait_for_timeout(1000)

            # submit button
            button = page.locator('button', has_text="Next")
            button.click()
            page.wait_for_timeout(1000)

            # Locate the last div with role="menuitem"
            last_menuitem_div = page.locator('div[role="menuitem"]').nth(2)
            last_menuitem_div.click()
            page.wait_for_timeout(1000)

            # check for the text
            text = page.locator('div', has_text="Assign to me").nth(-1)
            expect(text).to_be_visible()
            page.wait_for_timeout(1000)

        finally:
            # Stop tracing and save
            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            context.tracing.stop(path=trace_path)

            # Clean the trace
            from utils.trace_cleaner import trace_cleaner
            trace_cleaner(trace_path)

            browser.close()
