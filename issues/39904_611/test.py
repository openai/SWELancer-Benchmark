import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
from playwright.sync_api import sync_playwright, expect
import imaplib
import email
from email.header import decode_header
import re

# Gmail credentials with app-specific password
user_email = "playwright2user+1@gmail.com"
password = "zehr mglm gizg gjcc"


# Function to modify the verification link for local testing
def modify_verification_link_for_local_test(verification_link):
    if verification_link:
        modified_link = re.sub(r'https://new\.expensify\.com',
                               'https://dev.new.expensify.com:8082', verification_link)
        print(f"Modified link: {modified_link}")
        return modified_link
    return None

# Function to perform login using Playwright
def login_and_verify(p):
    browser = p.chromium.launch(headless=True,
            args=[
            "--ignore-certificate-errors",
            "--disable-web-security", 
            "--disable-features=IsolateOrigins,site-per-process"
        ])
    context = browser.new_context(ignore_https_errors=True, bypass_csp=True)

    # Create a new page within this context
    page = context.new_page()

    # Go to login page
    page.goto('https://dev.new.expensify.com:8082/')

    email_input = page.locator('input[type="email"]')
    email_input.wait_for()
    email_input.fill(user_email)

    continue_button = page.locator('button[tabindex="0"]')
    continue_button.wait_for()
    continue_button.click()

    page.wait_for_timeout(1000)

    try:
        continue_button = page.locator('button[tabindex="0"]')
        continue_button.wait_for()
        continue_button.click()
    except Exception:
        pass

    # Fetch and modify the verification link from the email
    verification_link = 'https://new.expensify.com/v/18587801/109829'
    modified_link = modify_verification_link_for_local_test(verification_link)

    # Open the modified link in a new browser tab
    if modified_link:
        new_tab = context.new_page()
        new_tab.goto(modified_link)

        # Monitor for "Here's your magic code" over a short period
        duration = 3
        check_interval = 0.1

        start_time = time.time()
        while time.time() - start_time < duration:
            # Perform an instant visibility check
            if new_tab.locator("text=Here's your magic code").is_visible():
                raise AssertionError(
                    "Unexpected 'Here's your magic code' screen appeared briefly.")

           
           
    else:
        print("Verification link not found or could not be modified.")

    return browser, page

# Main test function
def test():
    with sync_playwright() as p:
        browser, page = login_and_verify(p)

        if browser:
            page.wait_for_timeout(5000)
            browser.close()

