import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import email
import imaplib
import random
import re
import time
from playwright.sync_api import sync_playwright, expect
from utils.trace_cleaner import trace_cleaner


NEWDOT_URL = "https://dev.new.expensify.com:8082/"
OLDDOT_URL = "http://localhost:9000/"
EMAIL = "ikhanle001+34@gmail.com"
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

def test_50064():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=[
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process'
        ])

        context = browser.new_context(ignore_https_errors=True)
        try:

            context.tracing.start(title="test_50064", screenshots=True, snapshots=True)

            page1 = context.new_page()
            email = EMAIL
            page1.goto(NEWDOT_URL)
            page1.get_by_test_id("username").fill(email)
            page1.get_by_test_id("username").press("Enter")

            otp = "123456"
            page1.locator('input[data-testid="validateCode"]').fill(otp)
            page1.wait_for_timeout(4000)

            page2 = context.new_page()
            page2.goto(NEWDOT_URL)
            page1.wait_for_timeout(4000)
            page2.get_by_label("Track and budget expenses").click()
            expect(page2).to_have_url(re.compile(".*/onboarding/personal-details.*"))

        except Exception as e:
            print("An error occurred:", e)
            raise
        finally:

            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")

            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")

            context.close()
            browser.close()
