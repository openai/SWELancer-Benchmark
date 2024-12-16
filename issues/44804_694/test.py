import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import imaplib
import email
import re
import random
import time
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page


class EmailHandler:
    def __init__(self, email_address, password):
        # Validate email and password input
        if not self._validate_email(email_address):
            raise ValueError("Invalid email address format.")
        self.original_email = email_address
        self.password = password
        
        self.new_email = self._generate_new_email(email_address)
     
    def _validate_email(self, email_address):
        # Simple email validation
        return bool(re.match(r"[^@]+@[^@]+\.[^@]+", email_address))
    
    def _generate_new_email(self, email_address):
        # Add random number suffix to the email before the "@" symbol
        username, domain = email_address.split("@")
        # return f"{username}+{suffix}@{domain}"
        return f"{username}@{domain}"

    def get_email_address(self):
        # Return the generated email with "+" suffix
        return self.new_email

    def check_for_otp(self):
        # Connect to the Gmail server using IMAP
        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(self.original_email, self.password)
            mail.select("inbox")

            # Fetch all unread emails
            status, messages = mail.search(None, "UNSEEN")
            if status != "OK":
                print("No unread emails found.")
                return None

            email_ids = messages[0].split()
            # Start from the latest email by reversing the list
            email_ids = email_ids[::-1]  # Reverse order to process latest first

            # Iterate over each email until OTP is found
            for email_id in email_ids:
                # Fetch the email by ID
                status, msg_data = mail.fetch(email_id, "(RFC822)")
                if status != "OK":
                    print("Error fetching email.")
                    continue

                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])

                        # Check if the To address matches the generated new email
                        if msg["To"] == self.new_email:
                            # Extract OTP from the email body
                            otp_code = self._extract_otp_from_email(msg)
                            if otp_code:
                                # Delete the email containing the OTP
                                # mail.store(email_id, "+FLAGS", "\\Deleted")
                                # mail.expunge()  # Permanently removes deleted emails from the mailbox

                                # Logout and return OTP
                                mail.close()
                                mail.logout()
                                return otp_code

            # Logout if OTP not found in unread emails
            mail.close()
            mail.logout()
            print("No OTP found in unread emails.")
            return None

        except imaplib.IMAP4.error:
            print(
                "Failed to connect to Gmail. Please check your email address or password."
            )
            return None

    def _extract_otp_from_email(self, msg):
        # Extract OTP code from the email content
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
        # Find a 6-digit code in the email body
        match = re.search(r"\b\d{6}\b", text)
        return match.group(0) if match else None

TIMEOUT = 20000
NEWDOT_URL = "https://dev.new.expensify.com:8082/"
TEST_EMAIL = "turingtemp+177125@gmail.com"
APP_PASSWORD = "rxyc esdd vdad pamq"


def login_user(
    p: PlaywrightContextManager, email: str
) -> tuple[Browser, Page]:
    browser = p.chromium.launch(headless=True, args=[
        "--disable-web-security",
        "--disable-features=IsolateOrigins,site-per-process"
    ])

    context = browser.new_context()
    context.set_default_navigation_timeout(TIMEOUT)
    context.set_default_timeout(TIMEOUT)
    context.set_default_navigation_timeout(TIMEOUT)

    page = context.new_page()

    # Step 1: Open expensify url
    page.goto(NEWDOT_URL)
    
    # Step 2: Enter email and click continue
    page.locator('input[type="email"]').fill(email)
    page.get_by_role("button", name="Continue").click()
    page.wait_for_timeout(5000)
    account = EmailHandler(email_address=TEST_EMAIL, password=APP_PASSWORD)

    otp_code = "681395"
    print("otp_code", otp_code)
    page.keyboard.type(otp_code)

    try:
        # # Step 4: Select 'Track and budget expenses' in onboarding page and click Continue
        page.locator("text='Track and budget expenses'").click()
        page.get_by_role("button", name="Continue").click()

        # Step 5: Enter first name, last name and click continue
        page.locator('input[name="fname"]').fill("Test")
        page.locator('input[name="lname"]').fill("User")
        page.get_by_role("button", name="Continue").last.click()

        page.wait_for_timeout(5000)
        page.get_by_role("button", name="Get started").click()
    except:
        pass

    return browser, page


def logout_user(page: Page) -> str:
    account_settings_button = page.get_by_role("button", name="My Settings")
    account_settings_button.click()
    signout_button = page.get_by_role("menuitem", name="Sign out")
    signout_button.click()


def test_do_not_show_account_green_indicator_for_existing_user():
    with sync_playwright() as p:
        browser, page = login_user(p, TEST_EMAIL)
        account_settings_button = page.locator('button[aria-label="My settings"]')
        green_indicator = account_settings_button.locator('div[class="css-view-175oi2r"][style*="background-color: rgb(3, 212, 124);"][style*="border-color: rgb(252, 251, 249);"]')
        page.wait_for_timeout(4000)
        expect(green_indicator).not_to_be_visible()
        browser.close()

