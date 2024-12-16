import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import os
import time
import pytest
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page
from playwright.sync_api import sync_playwright, expect
import re, time
import os
import imaplib
import email
import re
import random
from utils.trace_cleaner import trace_cleaner

NEWDOT_URL = "https://dev.new.expensify.com:8082/"
OLDDOT_URL = "http://localhost:9000/"
# EMAIL = "turingvidhant+8@gmail.com"
# PASSWORD = "uotx fzkt kfeg dehz"
EMAIL = "testingtraineralpha+346g3423@gmail.com" # for example test+1234@gmail.com
PASSWORD = "mgwv wswl sclf etix" # it will be something like "sdib pxop ovyl uawy"


class IMAPOTPExtractor:
    def __init__(self, email_address, password):
        if not self._validate_email(email_address):
            raise ValueError("Invalid email address format.")
        self.original_email = email_address
        self.password = password

        random_suffix = random.randint(1000, 9999)
        current_timestamp = int(time.time())
        random_suffix = f"{current_timestamp}{random_suffix}"
    
    def _validate_email(self, email_address):
        return bool(re.match(r"[^@]+@[^@]+\.[^@]+", email_address))
    
    def set_new_email(self, email):
        self.new_email = email
    
    def check_for_otp(self):
        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(self.original_email, self.password)
            mail.select("inbox")
            
            status, messages = mail.search(None, "UNSEEN")
            if status != "OK":
                return None
            
            email_ids = messages[0].split()            
            email_ids = email_ids[::-1]

            for email_id in email_ids:
                status, msg_data = mail.fetch(email_id, '(RFC822)')
                if status != "OK":
                    continue
                
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])

                        if self.new_email in msg["To"]:
                            otp_code = self._extract_otp_from_email(msg)
                            if otp_code:
                                mail.store(email_id, '+FLAGS', '\\Deleted')
                                mail.expunge()
                                mail.close()
                                mail.logout()
                                return otp_code
            
            mail.close()
            mail.logout()
            return None

        except imaplib.IMAP4.error:
            return None

    def _extract_otp_from_email(self, msg):
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    email_body = part.get_payload(decode=True).decode()
                    otp_code = self._extract_otp(email_body)
                    if otp_code:
                        return otp_code
        else:
            email_body = msg.get_payload(decode=True).decode()
            otp_code = self._extract_otp(email_body)
            if otp_code:
                return otp_code
        return None

    def _extract_otp(self, text):
        match = re.search(r"\b\d{6}\b", text)
        return match.group(0) if match else None

gmail_account_helper = IMAPOTPExtractor(EMAIL, PASSWORD)

def create_workspace_and_enable_feature(page: Page, feature: str):
    """
    Creates a new workspace and enables a specified feature.

    Args:
        page (Page): The Playwright page object.
        feature (str): The feature to enable (e.g., "Invoices").
    """
    page.locator('button[aria-label="Workspaces"]').click()
    time.sleep(0.1)

    page.get_by_test_id("WorkspaceSwitcherPage").get_by_role(
        "button", name="New workspace"
    ).click()
    time.sleep(0.1)

    page.locator('div[aria-label="More features"]').click()
    time.sleep(0.1)

    # Toggle feature
    toggle_button = page.locator(f'button[aria-label="{feature}"]')
    if not toggle_button.is_checked():
        toggle_button.click()
        time.sleep(0.1)

    page.locator('div[aria-label="Tags"]').click()
    time.sleep(0.1)


def new_dot_login(page, email):
    page.goto(NEWDOT_URL)  
    page.locator('input[type="email"]').fill(email)
    page.wait_for_timeout(3000)
    page.get_by_role("button", name="Continue").nth(0).click()
    page.wait_for_timeout(3000)
    gmail_account_helper.set_new_email(email)
    page.locator('input[data-testid="validateCode"]').fill('123456')
    # page.get_by_role("button", name="Sign In").click()


def test_expensify():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, slow_mo=2000, args=["--disable-web-security", "--disable-feature=IsolaterOrigins,site-per-process"])
        first_user_context = browser.new_context(viewport={"width": 1000, "height": 550})
        # Start tracing
        first_user_context.tracing.start(screenshots=True, snapshots=True, sources=True)
        exception_raised = None
        try:
            page = first_user_context.new_page()
            page.wait_for_timeout(3000)
            new_dot_login(page, EMAIL)
            page.wait_for_timeout(3000)

            # Click second chat
            second_chat_button = page.locator(
                '[aria-label="Navigates to a chat"]').nth(0)

            second_chat_button.click()
            time.sleep(1)

            # Click Create button
            click_create_button = page.locator('button[aria-label="Create"]').last
            click_create_button.click()
            time.sleep(1)

            # Click assign task
            click_submit_expense_button = page.locator(
                "[aria-label='Assign task']")
            click_submit_expense_button.click()
            time.sleep(1)

            # fill title
            page.locator('input[aria-label="Title"]').fill("title something")
            time.sleep(1)

            # submit button
            button = page.locator('button', has_text="Next")
            button.click()
            time.sleep(1)

            # Locate the last div with role="menuitem"
            last_menuitem_div = page.locator('div[role="menuitem"]').nth(2)
            last_menuitem_div.click()
            time.sleep(1)

            # check for the text
            text = page.locator('div', has_text="Assign to me").nth(-1)
            expect(text).to_be_visible()
            time.sleep(1)
            
            page.close()
        except Exception as e:
            exception_raised = e
        finally:
            # Stop tracing and save
            first_user_context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            # Clean the trace
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            browser.close()
            if exception_raised:
                raise exception_raised
