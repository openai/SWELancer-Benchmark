import re
import time
from playwright.sync_api import sync_playwright
import random
import imaplib
import email as email_lib
from playwright.sync_api import sync_playwright, expect
import os

NEWDOT_URL = "https://dev.new.expensify.com:8082/"

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

    def set_new_email(self, email_address):
        self.new_email = email_address
    
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
                        msg = email_lib.message_from_bytes(response_part[1])

                        # Check if the To address matches the generated new email
                        if msg["To"] == self.new_email:
                            # Extract OTP from the email body
                            otp_code = self._extract_otp_from_email(msg)
                            if otp_code:
                                # Delete the email containing the OTP
                                mail.store(email_id, '+FLAGS', '\\Deleted')
                                mail.expunge()  # Permanently removes deleted emails from the mailbox
                                
                                # Logout and return OTP
                                mail.close()
                                mail.logout()
                                return otp_code

            # Logout if OTP not found in unread emails
            mail.close()
            mail.logout()
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


def launch_app(pw, headless=False, device=None, geolocation=None):
    browser = pw.chromium.launch(proxy = {"server": "http://localhost:8080"}, headless = False, args = ["--no-sandbox", "--disable-dev-shm-usage", "--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"], slow_mo = 2000, channel = "chromium")

    context_args = {}
    if device:
        context_args.update(pw.devices[device])
    if geolocation:
        context_args["geolocation"] = geolocation
        context_args["permissions"] = ["geolocation"]
    context = browser.new_context(**context_args)
    page = context.new_page()
    return browser, context, page


def login_user_with_otp(page, email, email_extractor):
    page.goto(NEWDOT_URL)

    page.get_by_role("textbox", name="Phone or email").fill(email)
    page.get_by_role("button", name="Continue").click()
   
    otp_input = page.locator('input[data-testid="validateCode"]')
    otp_input.fill('123456')


def test_main():
    with sync_playwright() as pw:
        # User-provided email and password
        email_address = "rgarciatammy4@gmail.com"
        password = "ezkm eepd sctl nanx"

        # Initialize the IMAPOTPExtractor
        email_extractor = IMAPOTPExtractor(email_address, password)
        email = "rgarciatammy4+144@gmail.com"
        email_extractor.set_new_email(email)


        browser, context, page = launch_app(pw)
        login_user_with_otp(page, email, email_extractor)

        # sometimes a hidden layer appears
        try:
            page.get_by_label("Close").click(timeout=1000)
        except:
            pass

        page.get_by_role("button", name="Reports").click()
        invoice_menu = page.get_by_role("menuitem", name="Invoices").count()
        assert invoice_menu == 0, "Invoice menu is visible for invitee user, Usser exists!"

        context.close()
        browser.close()