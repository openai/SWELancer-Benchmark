import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
import re
from playwright.sync_api import Playwright, sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page


def login_user(p: PlaywrightContextManager, user_email, first_name, last_name) -> tuple[Browser, Page, str]:
    # Launch the browser with ignore HTTPS errors option
    browser = p.chromium.launch(headless=True, args=["--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"],
    proxy={"server": "http://localhost:8080"})
    context = browser.new_context(ignore_https_errors=True)  # This will ignore SSL certificate errors
    page = context.new_page()

    # Step 1: Open expensify url
    page.goto('https://localhost:8082/') 

    # Step 2: Enter email and click continue
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(1000)
    # Step 3: Click join button
    
    page.get_by_role("button", name="Join").click()
    page.wait_for_timeout(5000)
        
    # Step 4: Select 'Track and budget expenses' in onboarding page and click Continue
    page.locator("text='Track and budget expenses'").click()

    # Step 5: Enter first name, last name and click continue
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()
    page.wait_for_timeout(5000)
    
    return browser, page, user_email


def test_merchant_info_field_is_required_appeared():
    with sync_playwright() as p:

        #Step 1: Login user2
        browser2, page2, user_email2 = login_user(p, "alicealiceoglu+20@mail.com", "Bob", "B")
        browser2.close()
        
        #Step 2: Login user1
        browser, page, user_email = login_user(p, "alicealiceoglu+412850@mail.com", "Alice", "A")
        page.pause()
        #Step 3: Search user2 to send message
        page.get_by_label("Start chat (Floating action)").click()
        page.get_by_text("Start chat").click()
        page.wait_for_timeout(1000)
        page.get_by_test_id("selection-list-text-input").fill(user_email2)
        
        #Step 4: Send message to User2
        page.get_by_label("Bob B").click()
        page.wait_for_timeout(1000)
        page.get_by_role("textbox").fill("Hello")
        page.wait_for_timeout(1000)
        page.get_by_label("Send").nth(1).click()
        page.wait_for_timeout(1000)

        #Step 5: Create new workspace
        page.get_by_label("Start chat (Floating action)").click()
        page.wait_for_timeout(1000)
        page.get_by_text("New workspace").click()
        page.wait_for_timeout(1000)

        #Step 6: Activate invoices
        page.get_by_text("More features").click()
        page.wait_for_timeout(1000)
        page.get_by_label("Send and receive invoices.").click()
        page.wait_for_timeout(5000)
        page.get_by_label("Back").click()
        page.wait_for_timeout(1000)

        #Step 7: Send invoices
        page.get_by_label("Start chat (Floating action)").click()
        page.get_by_text("Send invoice").click()
        page.wait_for_timeout(1000)
        page.get_by_label("Select a currency").click()
        page.get_by_test_id("selection-list-text-input").fill("TRY")
        page.wait_for_timeout(1000)
        page.get_by_label("TRY - TL").click()
        page.get_by_placeholder("0").fill("111")
        page.wait_for_timeout(1000)
        page.get_by_role("button", name="Next").click()
        page.wait_for_timeout(1000)
        page.get_by_test_id("selection-list").get_by_label("Bob B").click()
        page.wait_for_timeout(1000)
        page.get_by_label("Show more").click()
        page.wait_for_timeout(1000)
        page.get_by_role("button", name="Next").click()
        page.wait_for_timeout(1000)
        page.get_by_role("textbox", name="Your company name").fill("Turing")
        page.wait_for_timeout(1000)
        page.get_by_role("textbox", name="Your company website").click()
        page.wait_for_timeout(1000)
        page.get_by_role("textbox", name="Your company website").fill("https://turing.com")
        page.wait_for_timeout(1000)
        page.get_by_role("button", name="Send TRY 111.00 invoice").click()
        page.wait_for_timeout(1000)
        page.get_by_label("View details").click()
        page.wait_for_timeout(1000)
        page.get_by_text("Merchant").click()
        page.wait_for_timeout(1000)
        page.get_by_role("textbox", name="Merchant").click()
        page.wait_for_timeout(1000)
        page.get_by_role("button", name="Save").click()
        page.wait_for_timeout(1000)

        #Step 8: Assertion invoices
        # Locate the element and assert its visibility
        element = page.get_by_text("This field is required.")
        assert not element.is_visible(), "The text 'This field is required.' is not visible on the page."

        browser.close()
