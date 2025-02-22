import imaplib
import random
import re
import time
import email

from playwright.sync_api import sync_playwright, expect 
from playwright._impl._page import Page
import pytest




NEWDOT_URL = "https://dev.new.expensify.com:8082/"
OLDDOT_URL = "http://localhost:9000/"
EMAIL = "turingsampleopen+53608@gmail.com"
PASSWORD = "dmyi iqgn znbg kqii"

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
        return "123456"
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

def new_dot_login(page):
    email = EMAIL
    page.goto(NEWDOT_URL)  
    page.locator('input[type="email"]').fill(email)
    page.wait_for_timeout(2000)
    page.get_by_role("button", name="Continue").nth(0).click()
    page.wait_for_timeout(5000)
    gmail_account_helper.set_new_email(email)
    otp = gmail_account_helper.check_for_otp()
    page.locator('input[data-testid="validateCode"]').fill(otp)
    # page.get_by_role("button", name="Sign In").click()

def handle_route(route):
    """Artificially delay API responses."""
    time.sleep(25)  # Delay API call by 2 seconds
    route.continue_()  # Allow request to continue

def test_expensify_53608():
     with sync_playwright() as p:
        
        browser = p.chromium.launch(channel="chrome", headless=False, args=[
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
            ])
        page = browser.new_page()

        new_dot_login(page)

        page.get_by_label("My settings").click()
        page.wait_for_timeout(1000)

        page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()
        page.wait_for_timeout(1000)

        page.get_by_label("New workspace").click()
        page.wait_for_timeout(1000)

        page.get_by_label("More features").click()
        page.wait_for_timeout(1000)

        page.get_by_label("Sync your chart of accounts").click()
        page.wait_for_timeout(1000)

        page.get_by_label("Accounting").click()
        page.wait_for_timeout(1000)

        page.get_by_label("QuickBooks Desktop").locator("div").filter(has_text="Connect").nth(3).click()
        page.wait_for_timeout(1000)

        page.get_by_test_id("upgrade-button").click()
        page.wait_for_timeout(1000)

        page.get_by_test_id("confirmation-button").click()

        assert page.get_by_text("Open this link to connect").count() > 0, "Full page spinner is displayed"
