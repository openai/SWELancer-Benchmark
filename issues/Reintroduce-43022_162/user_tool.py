import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import email
import imaplib
import random
import re
import time
from playwright.sync_api import sync_playwright, expect
from utils.trace_cleaner import trace_cleaner  # Added import for trace cleaning

NEWDOT_URL = "https://dev.new.expensify.com:8082/"
EMAIL = "testingtraineralpha+235fq243@gmail.com"  # for example test+1234@gmail.com
PASSWORD = "mgwv wswl sclf etix"  # it will be something like "sdib pxop ovyl uawy"


class IMAPOTPExtractor:
    def __init__(self, email_address, password):
        # Validate email and password input
        if not self._validate_email(email_address):
            raise ValueError("Invalid email address format.")
        self.original_email = email_address
        self.password = password

        # Generate new random email using "+" prefix
        random_suffix = random.randint(1000, 9999)
        current_timestamp = int(time.time())
        random_suffix = f"{current_timestamp}{random_suffix}"
        self.new_email = self._generate_new_email(email_address, random_suffix)
        # self.new_email = self.original_email
    
    def _validate_email(self, email_address):
        # Simple email validation
        return bool(re.match(r"[^@]+@[^@]+\.[^@]+", email_address))
    
    def _generate_new_email(self, email_address, suffix):
        # Add random number suffix to the email before the "@" symbol
        username, domain = email_address.split('@')
        return f"{username}+{suffix}@{domain}"

    def get_new_email(self):
        # Return the generated email with "+" suffix
        return self.new_email
    
    def set_new_email(self, email):
        self.new_email = email
    
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
                status, msg_data = mail.fetch(email_id, '(RFC822)')
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
                                mail.store(email_id, '+FLAGS', '\\Deleted')
                                mail.expunge()  # Permanently removes deleted emails

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
            print("Failed to connect to Gmail. Please check your email address or password.")
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


gmail_account_helper = IMAPOTPExtractor(EMAIL, PASSWORD)

def generate_random_email():
    random_suffix = random.randint(1000, 9999)
    timestamp = int(time.time())
    # Modify this 
    return f"testingtraineralpha+{timestamp}{random_suffix}@gmail.com"

def new_dot_login(page, email):
    page.goto(NEWDOT_URL)
    page.get_by_test_id("username").fill(email)
    page.get_by_role("button", name="Continue").click()
    # Wait for OTP
    page.wait_for_timeout(2000)
    # gmail_account_helper.set_new_email(email)
    # otp = gmail_account_helper.check_for_otp()
    otp = "123456"
    page.get_by_test_id("SignInPage").get_by_test_id("validateCode").fill(otp)
    try:
        page.get_by_test_id("SignInPage").get_by_role("button", name="Sign in").click()
    except:
        pass
    page.get_by_text("Concierge").last.wait_for()


def test_settings_header_style():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, slow_mo=500, args=[
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"])
        context_args = {}
        context_args["geolocation"] = {"latitude": 37.7749, "longitude": 122.4194}
        context_args["permissions"] = ["geolocation"]
        context_args["ignore_https_errors"] = True
        first_user_context = browser.new_context(**context_args)

        # Start tracing
        first_user_context.tracing.start(screenshots=True, snapshots=True, sources=True)

        page = first_user_context.new_page()
        first_user_email = generate_random_email()

        try:
            # Step 1: Login user
            new_dot_login(page, EMAIL)

            # Step 2: Go to workspace settings
            my_settings_button = page.locator('button[aria-label="My settings"]')
            my_settings_button.wait_for()
            my_settings_button.click()
            page.wait_for_timeout(1000)
            workspace_settings_button = page.locator('div[aria-label="Workspaces"][role="menuitem"]')
            workspace_settings_button.wait_for()
            workspace_settings_button.click()
            page.wait_for_timeout(1000)

            # Step 3: Rocket icon checks
            rocket_icon = page.locator("div:nth-child(4) > div:nth-child(2) > div:nth-child(2) > div > div > div > div > div > div > div > div > div:nth-child(2) > div > div > svg")
            rocket_icon.wait_for()
            assert rocket_icon.count() == 1
            assert rocket_icon.get_attribute("viewBox") == "0 0 34 34"
            assert rocket_icon.get_attribute("width") == "48"
            assert rocket_icon.get_attribute("height") == "48"
            paths = rocket_icon.locator("path")
            assert paths.count() == 35
            first_path = paths.nth(0)
            assert first_path.get_attribute("fill") == "#5BE3AA"

            # Step 4: "Create new workspace" should be visible
            h1_styled_title = page.locator('div[style*="font-size: 22px;"]', has_text="Create a workspace")
            expect(h1_styled_title).to_be_visible()

            page.wait_for_timeout(2000)
        except Exception as e:
            # Re-raise after capturing trace
            raise e
        finally:
            # Stop tracing and save
            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            first_user_context.tracing.stop(path=trace_path)
            # Clean trace
            trace_cleaner(trace_path)

            browser.close()
