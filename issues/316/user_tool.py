import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page
from utils.trace_cleaner import trace_cleaner


def login_user(p: PlaywrightContextManager, user_email) -> tuple[Browser, Page, str]:

    browser = p.chromium.launch(channel='chrome', headless=True, slow_mo=500,
        proxy = {"server": "http://127.0.0.1:8080/"},
        args=[
            "--ignore-certificate-errors",
            "--disable-web-security", 
            "--disable-features=IsolateOrigins,site-per-process"
        ])
    context_args = {}
    context_args["geolocation"] = {"latitude": 37.7749, "longitude": 122.4194}
    context_args["permissions"] = ["geolocation"]
    context_args["ignore_https_errors"] = True
    context = browser.new_context(**context_args)
    page = context.new_page()
    user_email = user_email

    page.goto('https://127.0.0.1:8082/')

    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(1000)

    otp = '123456'
    page.get_by_test_id("SignInPage").get_by_test_id("validateCode").fill(otp)
    page.wait_for_timeout(2000)
    return browser, page, user_email


def test_disable_category():
    with sync_playwright() as p:
        browser_b, page_b, user_email_b = login_user(p, "t1533148+123@gmail.com")
        # Get the context from the page
        context = page_b.context
        # Start tracing
        context.tracing.start(screenshots=True, snapshots=True, sources=True)

        try:
            page_b.wait_for_timeout(2000)
            page_b.get_by_test_id("7823501529575664").click()
            page_b.wait_for_timeout(1000)
            page_b.get_by_label("View details").click()
            
            expense1 = page_b.get_by_text("Cash").nth(1)
            expense1.click()
            page_b.wait_for_timeout(1000)
            
            cat = page_b.get_by_text("Category", exact=True)
            cat.click()
            page_b.wait_for_timeout(2000)
            
            recent_section = page_b.get_by_text("Recent")
            all_section = page_b.get_by_text("All")
            search_section = page_b.locator('input[aria-label="Search"]')
            
            expect(recent_section).not_to_be_visible()
            expect(all_section).not_to_be_visible()
            expect(search_section).not_to_be_visible()
            
            page_b.wait_for_timeout(3000)
        finally:
            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            context.tracing.stop(path=trace_path)
            trace_cleaner(trace_path)
            browser_b.close()


if __name__ == '__main__':
    test_disable_category()