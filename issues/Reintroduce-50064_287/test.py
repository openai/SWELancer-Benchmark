import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)



import logging
import sys

from playwright.sync_api import sync_playwright, expect
import re
import imaplib
import email

# Expensify app URL
NEWDOT_URL = "https://dev.new.expensify.com:8082"
OLDDOT_URL = "http://127.0.0.1:9000/"

# Logger
logging.basicConfig(level=logging.INFO, stream=sys.stdout, format="%(message)s")
LOGGER = logging.getLogger(__name__)

class IMAPOTPExtractor:
    def __init__(self, email_address, password):
        # Validate email and password input
        if not self._validate_email(email_address):
            raise ValueError("Invalid email address format.")
        self.original_email = email_address
        self.password = password

        self.new_email = self._generate_new_email(email_address, "1000243")
    
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
                                mail.expunge()  # Permanently removes deleted emails from the mailbox
                                
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


def launch_app(pw, headless=True, device=None, geolocation=None):
    """
    Launch the Expensify app with device emulation.
    """
    # Set up the device emulation for Pixel 7
    browser = pw.chromium.launch(headless=headless, args=[
        "--disable-web-security",
        "--disable-features=IsolateOrigins,site-per-process"
    ])
    if geolocation:
        context_args["geolocation"] = geolocation
        context_args["permissions"] = ["geolocation"]
    context = browser.new_context(**context_args)
    page = context.new_page()
    return browser, context, page

def test_check_onboarding_dialogue():
    
    """
    Demonstrate the Expensify app email login verification for mobile web.
    """
    with sync_playwright() as pw:
        email_address = "turingtemp@gmail.com"
        password = "rxyc esdd vdad pamq"
        account = IMAPOTPExtractor(email_address, password)
        new_email_address = account.get_new_email()
        

        browser = pw.chromium.launch(headless=True, channel="chrome", args=[
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ])
        page = browser.new_page()
        page.goto(NEWDOT_URL)

        page.wait_for_timeout(2000)
    
        # Login user
        page.get_by_role("textbox", name="Phone or email").fill(new_email_address)
        page.get_by_role("button", name="Continue").click()
        page.get_by_role("button", name="Join").click()
        expect(page.locator("text=What do you want to do today?")).to_be_visible()

        # Goto the base url again
        page.goto(NEWDOT_URL)
        page.wait_for_timeout(2000)
        page.locator("text='Track and budget expenses'").click()
        page.wait_for_timeout(2000)
        assert page.locator('input[name="fname"]').is_visible()


        # Close the browser
        browser.close()


if __name__ == "__main__":
    test_check_onboarding_dialogue()

