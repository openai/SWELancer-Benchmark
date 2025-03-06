import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
from playwright.sync_api import sync_playwright, expect
import re 



static_email = "testuserexpensify1+35@gmail.com"

def test_open_page_and_validate_row_hover():
    site_url = 'https://dev.new.expensify.com:8082/concierge'
    timestamp = int(time.time())
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, slow_mo=1000, args=["--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"])
        page = browser.new_page()

        page.goto(site_url) 

        phone_or_email_input = page.locator('input[type="email"]')
        phone_or_email_input.fill(static_email)

        continue_button = page.locator('button[tabindex="0"]')
        continue_button.click()

        join_button = page.get_by_role("button", name="Join")
        join_button.click()



        page.locator("div").filter(has_text=re.compile(r"^Something else$")).first.click()
        page.locator("body").press("Enter")


        page.locator('input[name="fname"]').fill("Account")
        page.locator('input[name="lname"]').fill(f"{timestamp}")
        page.get_by_role("button", name="Continue").last.click()
        page.get_by_role("button", name="Get Started").click()


        page.goto(site_url)

        concierge_button = page.locator('button[aria-label="concierge@expensify.com"]', has_text="Concierge").first
        concierge_button.wait_for(state="visible")
        expect(concierge_button).to_be_visible()


        browser.close()
