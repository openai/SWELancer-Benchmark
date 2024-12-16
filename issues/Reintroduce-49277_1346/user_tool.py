import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import email
import imaplib
import random
import re
import time
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page
from utils.trace_cleaner import trace_cleaner

# Constants for URLs and credentials
NEWDOT_URL = "https://dev.new.expensify.com:8082/"
OLDDOT_URL = "http://localhost:9000/"
EMAIL = "ikhanle001+23@gmail.com"
PASSWORD = "dzcr knad otxp bsuz"

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

# Initialize the OTP extractor
gmail_account_helper = IMAPOTPExtractor(EMAIL, PASSWORD)


def login_user(p: PlaywrightContextManager, first_name="Abhishek", last_name="M") -> tuple[Browser, Page, str]:
    # Launch chromiun and open new page
    browser = p.chromium.launch(headless=True, args=[
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process'
        ])
    page = browser.new_page()
    user_email = EMAIL

    # Step 1: Open expensify url
    page.goto('https://dev.new.expensify.com:8082/')

    page.locator('input[type="email"]').fill(user_email)
    page.wait_for_timeout(2000)
    page.get_by_role("button", name="Continue").nth(0).click()
    page.wait_for_timeout(10000)
    # gmail_account_helper.set_new_email(user_email)
    # otp = gmail_account_helper.check_for_otp()
    otp = "123456"
    page.locator('input[data-testid="validateCode"]').fill(otp)

    return browser, page, user_email


def test_the_issue():
    with sync_playwright() as p:
        trace_path = "/app/expensify/user_tool/output_browser1.zip"
        p.tracing.start(screenshots=True, snapshots=True, sources=True)
        try:
            browser, page, user_email = login_user(p)
            page.wait_for_timeout(1000)

            page.get_by_label("My settings").last.click()
            page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").get_by_text("Workspaces").click()
            page.get_by_label("New workspace").first.click()
            page.get_by_label("More features").last.click()
            page.get_by_label("Configure when receipts are").click()
            page.get_by_role("button", name="Upgrade").click()
            page.get_by_role("button", name="Got it, thanks").click()
            page.get_by_label("Configure how spend is").click()
            page.get_by_test_id("WorkspaceInitialPage").get_by_text("Workflows").click()
            page.get_by_label("Require additional approval").click()

            # Capture approver display name in workflow page
            workflow_approver_name = page.locator('//div[@aria-label="Approver"]').text_content().replace('Approver', '').strip()

            # Go to Categorize and open the Advertising category
            page.click('//div[@aria-label="Categories"]')
            page.locator('//button[@aria-label="Advertising"]').first.click()

            # Verify that the approver field shows the correct display name
            page.locator('//div[contains(text(), "Approver")]').nth(1).click()
            page.click('//div[contains(text(), "Admin")]')
            approver_name_in_category = page.locator('//div[contains(text(), "Approver")]/following-sibling::div//div[@class="css-text-146c3p1 r-maxWidth-dnmrzs r-overflow-1udh08x r-textOverflow-1udbk01 r-wordWrap-1iln25a"]')
            expect(approver_name_in_category).to_have_text(workflow_approver_name)
        except Exception as e:
            raise e
        finally:
            p.tracing.stop(path=trace_path)
            trace_cleaner(trace_path)
