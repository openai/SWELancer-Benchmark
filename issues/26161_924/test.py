import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import re
import time
from playwright.sync_api import Playwright, sync_playwright, expect

# For this test we have to put a valid email id used before
# in order to to directed to the magic code page

def test_console_error():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=["--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"])
        context = browser.new_context()

        # First Page
        page = context.new_page()
        page.goto("https://dev.new.expensify.com:8082/")
        # Second page
        page1 = context.new_page()
        page1.goto("https://dev.new.expensify.com:8082/")

        # Login expensify
        phone_or_email_input = page1.locator('input[type="email"]')
        expect(phone_or_email_input).to_be_visible()
        # enter your valid email id
        phone_or_email_input.fill("jellystarfish99@gmail.com")
        page1.get_by_role("button", name="Continue").click()

        page1.wait_for_timeout(1000)

        expect(page.get_by_text("You've opened the login page")).to_be_visible()
        expect(page.get_by_text("Another login page is open.")).to_be_visible()

        page1.wait_for_timeout(1000)

        context.close()
        browser.close()
