import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
from playwright.sync_api import sync_playwright, expect
import imaplib
import email
from email.header import decode_header
import re


user_email = "playwright00700@gmail.com"
password = "cpoo vncg atzb frfd"


def get_magic_code(user_email, password, retries=5, delay=5):
    # Connect to the server
    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    imap.login(user_email, password)

    # Mark all existing emails as read
    imap.select("inbox")
    status, all_emails = imap.search(None, 'UNSEEN')
    if status == "OK":
        email_ids = all_emails[0].split()
        for email_id in email_ids:
            imap.store(email_id, '+FLAGS', '\\Seen')  # Mark as read

    # Retry logic for finding the magic code
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
    
    # Step 1: Login
    permissions = ['clipboard-read', 'clipboard-write']
    browser = p.chromium.launch(headless=True, args=[ "--disable-web-security", "--disable-features=IsolateOrigins, site-per-process" ])


    page = browser.new_page()
    page.goto('https://dev.new.expensify.com:8082/') 

    phone_or_email_input = page.locator('input[type="email"]')
    expect(phone_or_email_input).to_be_visible()
    phone_or_email_input.fill(user_email)
    page.wait_for_timeout(5000)
    page.get_by_role("button", name="Continue").click()
    page.wait_for_timeout(1000)

    magic_code = '123456'#get_magic_code(user_email, password, retries=3, delay=10)

    validate_code_input = page.locator('input[name="validateCode"]')
    expect(validate_code_input).to_be_visible()
    validate_code_input.fill(magic_code)

    page.wait_for_timeout(1000)

    return browser, page


def test_check_style_setup_button():
    with sync_playwright() as p:
        # Step 1: Login
        browser, page = login(p, False)

        time.sleep(10)

        # Navigate through the UI
        page.get_by_label("My settings").click()
        page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").get_by_text("Workspaces").click()
        page.wait_for_timeout(2000)
        page.locator("div").filter(has_text=re.compile(r"^New workspace$")).first.click()
        page.wait_for_timeout(2000)
        page.get_by_label("More features").locator("div").filter(has_text="More features").nth(3).click()
        page.wait_for_timeout(2000)
        page.get_by_label("Sync your chart of accounts").click()
        page.wait_for_timeout(2000)
        page.get_by_label("Accounting").locator("div").filter(has_text="Accounting").nth(3).click()
        
        # Locate the button element without clicking
        button = page.get_by_label("Quickbooks Online").locator("div").filter(has_text="Set up").nth(1)

        # Evaluate the computed style of the button and check 'justify-content'
        justify_content = button.evaluate("element => window.getComputedStyle(element).justifyContent")
        assert justify_content == "center", f"Style not found"

        # Print confirmation if the style matches
        print("Assertion passed: Button has 'justify-content: center'.")