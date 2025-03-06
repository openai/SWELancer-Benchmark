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
EMAIL = "turingvidhant+109@gmail.com"
PASSWORD = ""

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


def new_dot_login(page, email):
    page.goto(NEWDOT_URL)
    page.locator('input[type="email"]').fill(email)
    page.wait_for_timeout(3000)
    page.get_by_role("button", name="Continue").nth(0).click()
    page.wait_for_timeout(3000)
    gmail_account_helper.set_new_email(email)
    otp = gmail_account_helper.check_for_otp()
    page.locator('input[data-testid="validateCode"]').fill("123456")
    try:
        page.get_by_role("button", name="Sign In").click()
    except:
        pass


def launch_browser(pw, headless=True, device=None, geolocation=None):
    """
    Launch the browser.
    """
    browser = pw.chromium.launch(headless=headless)
    context_args = {}
    if device:
        context_args.update(pw.devices[device])
    if geolocation:
        context_args["geolocation"] = geolocation
        context_args["permissions"] = ["geolocation"]
    context = browser.new_context(**context_args)
    page = context.new_page()
    return browser, context, page


def test_expensify():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=[
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ])

        first_user_context = browser.new_context(ignore_https_errors=True)

        first_user_context.tracing.start(screenshots=True, snapshots=True)
        page = first_user_context.new_page()

        try:
            page.wait_for_timeout(3000)
            new_dot_login(page, EMAIL)
            page.wait_for_timeout(3000)

            my_settings = page.get_by_label("My settings")
            expect(my_settings).to_be_visible()
            my_settings.click()
            page.wait_for_timeout(1000)

            work_spaces = page.locator('div[aria-label="Workspaces"]')
            expect(work_spaces).to_be_visible()
            work_spaces.click()
            page.wait_for_timeout(1000)
            my_work = page.locator("div:nth-child(2) > div:nth-child(2) > div > div:nth-child(2) > div > div")
            expect(my_work).to_be_visible()
            my_work.click()
            page.wait_for_timeout(1000)

            features = page.locator('div[aria-label="Members"]')
            expect(features).to_be_visible()
            features.click()
            page.wait_for_timeout(1000)

            invite_member = page.locator('button:has-text("Invite member")')
            expect(invite_member).to_be_visible()
            invite_member.click()
            page.wait_for_timeout(1000)

            page.locator('input[aria-label="Name, email, or phone number"]').fill("qwerty@gmail.com")
            page.wait_for_timeout(1000)

            page.locator(f'button[aria-label="qwerty@gmail.com"]').nth(0).click()
            page.wait_for_timeout(1000)

            page.locator('input[aria-label="Name, email, or phone number"]').fill("asdfg@gmail.com")
            page.wait_for_timeout(1000)

            page.locator(f'button[aria-label="asdfg@gmail.com"]').nth(0).click()
            page.wait_for_timeout(1000)

            assert page.locator('button[aria-label="qwerty@gmail.com"]').nth(0).is_visible()
            assert page.locator('button[aria-label="asdfg@gmail.com"]').nth(0).is_visible()

            page.locator('input[aria-label="Name, email, or phone number"]').fill("qwerty@gmail.com")
            page.wait_for_timeout(1000)

            assert page.locator('button[aria-label="qwerty@gmail.com"]').nth(0).is_visible()

            page.wait_for_timeout(1500)
        finally:

            first_user_context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")

            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            page.close()
            browser.close()
