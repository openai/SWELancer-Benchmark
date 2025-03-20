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
EMAIL = "turingvidhant+113@gmail.com"
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

        first_user_context.tracing.start(screenshots=True, snapshots=True, sources=True)

        page = first_user_context.new_page()
        try:
            page.wait_for_timeout(3000)

            new_dot_login(page, EMAIL)
            page.wait_for_timeout(3000)


            page.get_by_role("button", name="Start chat (Floating action)").click()
            page.get_by_text("Submit expense").click()
            page.get_by_test_id("IOURequestStartPage").get_by_role("button", name="Manual").click()


            amount_field_locator = (
                page.get_by_test_id("IOURequestStartPage")
                .locator("input[class='css-textinput-11aywtz r-placeholderTextColor-6taxm2']")
                .all()[0]
            )


            amount = "12345.67"
            temp = amount.split(".")
            digits_after_decimal = temp[1].strip()
            digits_before_decimal = temp[0].strip()


            amount_field_locator.fill(amount)


            for _ in range(len(digits_after_decimal) + 1):
                page.keyboard.press("ArrowLeft")

                page.wait_for_timeout(200)

            for _ in range(len(digits_before_decimal) + 1):
                page.keyboard.press("Backspace")

                page.wait_for_timeout(200)


            expected_amount = f"0.{digits_after_decimal}"
            actual_amount = amount_field_locator.input_value()
            assert_message = f"Amount should be {expected_amount} after removing all the digits before the decimal point"
            assert actual_amount == expected_amount, assert_message


            for x in digits_before_decimal:
                page.keyboard.press(x)

                page.wait_for_timeout(200)
            expected_amount = f"0{digits_before_decimal}.{digits_after_decimal}"
            actual_amount = amount_field_locator.input_value()
            assert_message = f"Amount should be {expected_amount} after the update"
            assert actual_amount == expected_amount, assert_message

            page.wait_for_timeout(1500)
        except Exception as e:

            raise e
        finally:

            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            first_user_context.tracing.stop(path=trace_path)
            trace_cleaner(trace_path)

            page.close()
            browser.close()
