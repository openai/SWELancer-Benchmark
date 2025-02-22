import email
import imaplib
import logging
import re
from email.header import decode_header

from playwright._impl._page import Page
from playwright.sync_api import sync_playwright, expect

NEW_DOT_URL = "https://dev.new.expensify.com:8082"
ONE_SECOND = 1000
TWO_SECONDS = 2000
THREE_SECONDS = 3000
FIVE_SECONDS = 5000
email_address = "adebayovicktor0+test43726@gmail.com"

# Sign In to Expensify
def sign_in_new_dot(page: Page, email: str, url: str=None):
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
    otp = '123456'
    page.get_by_test_id("validateCode").fill(otp)
    page.wait_for_timeout(TWO_SECONDS)

    # Wait sign in to complete
    page.get_by_text("Please enter the magic code").wait_for(state="hidden")
    page.wait_for_timeout(THREE_SECONDS)

def generate_email():
    return f"adebayovicktor0+test52071@gmail.com"

def test_spinner_shows_when_company_card_is_selected():
    """
    Test to verify that the send button is focused when the modal is opened
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False,
                                    proxy = {"server": "http://127.0.0.1:8080/"},
                                    args=[
                                        "--ignore-certificate-errors",
                                        "--disable-web-security",
                                        "--disable-features=IsolateOrigins,site-per-process"
                                    ],
                                    slow_mo=1000
                                    )
        user_email = generate_email()
        context = browser.new_context()
        page = context.new_page()
        sign_in_new_dot(page, user_email)
        page.get_by_label("Inbox").click()
        page.get_by_label("My settings").click()
        page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").get_by_text("Workspaces").click()
        page.get_by_role("button", name="row").click()
        # Create a CDP session
        cdp = context.new_cdp_session(page)
    
        # Enable network domain
        cdp.send("Network.enable")
    
        # Emulate specific network conditions (to simulate slow api response):
        cdp.send("Network.emulateNetworkConditions", {
            "offline": False,
            "latency": 400,             # Additional latency (ms)
            "downloadThroughput": 10 * 1024 / 8,  # ~10 kb/s
            "uploadThroughput": 10 * 1024 / 8,    # ~10 kb/s
        })
    
        page.get_by_test_id("WorkspaceInitialPage").get_by_label("Company cards").click()
        expect(page.locator('div[role="progressbar"]')).to_be_visible()