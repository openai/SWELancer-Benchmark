import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import imaplib
import email
from playwright.sync_api import sync_playwright
from utils.trace_cleaner import trace_cleaner


EMAIL_USERNAME1 = "testotpverif+111@gmail.com"
EMAIL_USERNAME2 = "testotpverif+222@gmail.com"
EMAIL_PASSWORD = "ghka tmuf vpio patv"
EXPENSIFY_URL = "https://dev.new.expensify.com:8082/"

 
def login_user(email_username, page):
    """
    Log into the Expensify app.
    """
    page.goto(EXPENSIFY_URL)

    page.get_by_test_id("username").fill(email_username)
    page.get_by_role("button", name="Continue").click()
    otp_code = '101010'
    page.get_by_test_id("SignInPage").get_by_test_id("validateCode").fill(otp_code)
    sign_in_button = page.get_by_test_id("SignInPage").get_by_role("button", name="Sign in")
    page.wait_for_timeout(1000)
    if sign_in_button.is_visible():
        sign_in_button.click()
    page.wait_for_timeout(2000)

    

def submit_expense(page, recipient_email):

    plus_button = page.locator('button[aria-label="Start chat (Floating action)"]')
    plus_button.wait_for()
    plus_button.click()
    page.wait_for_timeout(1000)


    submit_expense_button = page.locator('div[aria-label="Submit expense"]').first
    submit_expense_button.wait_for()
    submit_expense_button.click()
    page.wait_for_timeout(1000)


    manual_button = page.locator('button[aria-label="Manual"]').wait_for()
    manual_button = page.locator('button[aria-label="Manual"]')
    manual_button.wait_for()
    manual_button.click()
    page.wait_for_timeout(1000)


    page.locator('input[type="text"]').fill("500")
    page.keyboard.press("Enter")
    page.wait_for_timeout(1000)


    email_input = page.locator('input[aria-label="Name, email, or phone number"]')
    email_input.wait_for()
    email_input.fill(recipient_email)
    page.wait_for_timeout(1000)


    recipient_option = page.locator(f'div:has-text("{recipient_email}")').last
    recipient_option.wait_for()
    recipient_option.click()
    page.wait_for_timeout(1000)
    page.keyboard.press("Enter")
    page.wait_for_timeout(1000)


def test_expenses_members_list():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=["--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"], slow_mo=500)
        context1 = None
        context2 = None
        try:
            # Create first context and start tracing
            context1 = browser.new_context()
            context1.tracing.start(screenshots=True, snapshots=True, sources=True)
            page1 = context1.new_page()

            login_user(email_username=EMAIL_USERNAME1, page=page1)
            submit_expense(page1, EMAIL_USERNAME2)

            # Continue with second context
            context2 = browser.new_context()
            context2.tracing.start(screenshots=True, snapshots=True, sources=True)
            page2 = context2.new_page()
            login_user(email_username=EMAIL_USERNAME2, page=page2)

            page2.get_by_label("Start chat (Floating action)").click()
            page2.get_by_label("Start chat", exact=True).click()
            page2.get_by_test_id("selection-list-text-input").click()
            page2.get_by_test_id("selection-list-text-input").fill(EMAIL_USERNAME1)
            page2.get_by_test_id("NewChatPage").get_by_label("Test 1").click()
            page2.get_by_role("textbox").click()
            page2.get_by_role("textbox").fill("hi")
            page2.keyboard.press("Enter")
            submit_expense(page2, EMAIL_USERNAME1)
            page2.wait_for_timeout(3000)

            page2.get_by_text("Test2 owes").first.click()
            try:
                page2.get_by_label("Test2 owes").first.click()
            except Exception:
                page2.get_by_text("Test2 owes").nth(1).click()
            page2.get_by_label("Members").click()
            page2.wait_for_timeout(2000)

            first_user_div = page2.locator(f'button[aria-label*="Test"]:has(div:has-text("{EMAIL_USERNAME1}"))')
            second_user_div = page2.locator(f'button[aria-label*="Test2"]:has(div:has-text("{EMAIL_USERNAME2}"))')
            first_user_div_count = first_user_div.count()
            second_user_div_count = second_user_div.count()

            assert first_user_div_count == 1, f"First user div count is {first_user_div_count}"
            assert second_user_div_count == 1, f"Second user div count is {second_user_div_count}"

        finally:
            # Export tracing and clean up for context1
            if context1 is not None:
                trace_path1 = "/app/expensify/user_tool/output_browser1.zip"
                try:
                    context1.tracing.stop(path=trace_path1)
                except Exception as e:
                    print(f"Error stopping tracing for context1: {e}")
                try:
                    trace_cleaner(trace_path1)
                except Exception as e:
                    print(f"Error cleaning trace for context1: {e}")
                try:
                    context1.close()
                except Exception as e:
                    print(f"Error closing context1: {e}")
            
            # Export tracing and clean up for context2
            if context2 is not None:
                trace_path2 = "/app/expensify/user_tool/output_browser2.zip"
                try:
                    context2.tracing.stop(path=trace_path2)
                except Exception as e:
                    print(f"Error stopping tracing for context2: {e}")
                try:
                    trace_cleaner(trace_path2)
                except Exception as e:
                    print(f"Error cleaning trace for context2: {e}")
                try:
                    context2.close()
                except Exception as e:
                    print(f"Error closing context2: {e}")
            try:
                browser.close()
            except Exception as e:
                print(f"Error closing browser: {e}")


if __name__ == "__main__":
    test_expenses_members_list()
