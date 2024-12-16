import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import os
import pytest
import time
from playwright.sync_api import sync_playwright, expect
import imaplib
import email
from email.header import decode_header
import re

from utils.trace_cleaner import trace_cleaner

password = "ywvy nytt kjig mscy"
user_email = "jellystarfish99@gmail.com"

def get_magic_code(user_email, password, retries=5, delay=10):

    # Connect to the server
    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    imap.login(user_email, password)

    for attempt in range(retries):

        imap.select("inbox")
        status, messages = imap.search(None, '(UNSEEN SUBJECT "Expensify magic sign-in code:")')

        if status == "OK":
            email_ids = messages[0].split()

            if email_ids:
                latest_email_id = email_ids[-1]
                status, msg_data = imap.fetch(latest_email_id, "(RFC822)")

                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        subject, encoding = decode_header(msg["Subject"])[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding or "utf-8")

                        # Search for the magic code in the subject
                        match = re.search(r"Expensify magic sign-in code: (\d+)", subject)
                        if match:
                            code = match.group(1)
                            imap.logout()
                            return code
            else:
                print("No unread emails found with the subject. Retrying...")
        else:
            print("Failed to retrieve emails. Retrying...")

        # Wait for the specified delay before trying again
        time.sleep(delay)

    imap.logout()
    print("Max retries reached. Email not found.")
    return None

def login(p, if_phone=False, first_name="John", last_name="Cena"):

    # step 1: Login
    permissions = ['clipboard-read', 'clipboard-write']
    browser = p.chromium.launch(headless=True, args=["--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"])


    if if_phone:
        phone = p.devices['iPhone 12 Pro']
        context = browser.new_context(**phone, permissions=permissions, reduced_motion='no-preference')
    else:
        context = browser.new_context()

    page = context.new_page()

    page.goto('https://dev.new.expensify.com:8082/') 

    phone_or_email_input = page.locator('input[type="email"]')
    expect(phone_or_email_input).to_be_visible()
    phone_or_email_input.fill(user_email)

    continue_button = page.locator('button[tabindex="0"]')
    expect(continue_button).to_be_visible()
    continue_button.click()

    page.wait_for_timeout(5000)

    # magic_code = get_magic_code(user_email, password, retries=3, delay=10)
    magic_code = "111111"

    validate_code_input = page.locator('input[data-testid="validateCode"]')
    expect(validate_code_input).to_be_visible()
    validate_code_input.fill(magic_code)

    page.wait_for_timeout(2000)

    # sign_in_div = page.locator('div:has-text("Sign in")').first
    # expect(sign_in_div).to_be_visible()
    # sign_in_div.click()


    return browser, page

def test_duplicate_contact_methods():
    with sync_playwright() as p:
        browser, page = login(p, False)
        context = page.context
        # Start tracing
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        
        try:
            page.get_by_label("My settings").click()
            page.get_by_label("jellystarfish99@gmail.com").click()
            page.get_by_role("button", name="New contact method").click()
            page.get_by_role("textbox", name="Email/Phone number").fill("+919920002597")
            page.get_by_role("button", name="Add").click()
            page.wait_for_timeout(5000)
            # magic_code1 = get_magic_code(user_email, password, retries=3, delay=10)
            magic_code1 = "111111"
            page.get_by_test_id("ValidateCodeActionModal").get_by_role("textbox").fill(magic_code1)
            duplicate_added = False

            page.wait_for_timeout(5000)
            page.get_by_role("button", name="New contact method").click()
            page.get_by_role("textbox", name="Email/Phone number").fill("+919920002597")
            page.get_by_role("button", name="Add").click()
            page.wait_for_timeout(5000)
            # magic_code2 = get_magic_code(user_email, password, retries=3, delay=10)
            magic_code2 = "111111"
            page.get_by_test_id("ValidateCodeActionModal").get_by_role("textbox").fill(magic_code2)
            duplicate_added = True

        except Exception:
            # Let the test fail but still ensure cleanup.
            pass
        finally:
            if 'duplicate_added' in locals() and duplicate_added:
                page.get_by_test_id("ContactMethodsPage").get_by_label("2597").nth(1).click()
                page.get_by_text("Remove").click()
                page.get_by_role("button", name="Yes, continue").click()
                pytest.fail('Test Failed able to add duplicate phone numbers')
            else:
                page.get_by_test_id("NewContactMethodPage").get_by_label("Back").click()

            page.get_by_test_id("ContactMethodsPage").get_by_label("2597").click()
            page.get_by_text("Remove").click()
            page.get_by_role("button", name="Yes, continue").click()

            # Stop tracing and clean up
            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            # Close the browser
            browser.close()
