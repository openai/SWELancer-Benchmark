import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from playwright._impl._page import Page

# Sign In to Expensify
def sign_in_new_dot(page: Page, email: str, password: str):
    page.goto("https://dev.new.expensify.com:8082/")
    
    page.get_by_test_id("username").fill(email)
    page.get_by_role("button", name="Continue").click()
    page.wait_for_timeout(2000)

    otp = "123456"
    page.get_by_test_id("validateCode").fill(otp)
    page.get_by_text("Please enter the magic code").wait_for(state="hidden")
    return page


def test_invalid_currency():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=[
            "--ignore-certificate-errors",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ])
        context = browser.new_context()
        page = context.new_page()

        email = "bobexpensifytest+12385484515@gmail.com"
        password = "aymv mpce nrvd cvye "

        page = sign_in_new_dot(page, email, password)

        page.wait_for_timeout(2000)

        page.goto("https://dev.new.expensify.com:8082/r/4327846041984602")
        
        report_id = "4327846041984602"
        statement = f'Onyx.merge("report_{report_id}",{{currency: null}});'

        page.wait_for_timeout(2000)

        page.evaluate(statement)

        error_text = page.locator('div[dir="auto"]', has_text="Uh-oh, something went wrong!")
        expect(error_text).not_to_be_visible()