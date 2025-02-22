from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page
import re, time
import imaplib
import email

EMAIL = "mancity9271+678@gmail.com"
APP_PASSWORD = "aplp neek apqv cjbr"
NEWDOT_URL = "https://dev.new.expensify.com:8082/"


# Function to log in an existing user using get_otp flow
class IMAPOTPExtractor:
    def __init__(self, email_address, password):
        if not self._validate_email(email_address):
            raise ValueError("Invalid email address format.")
        self.original_email = email_address
        self.password = password

    def _validate_email(self, email_address):
        return bool(re.match(r"[^@]+@[^@]+\.[^@]+", email_address))
    
    def set_new_email(self, email):
        self.new_email = email

    def check_for_otp(self):
        #In case we are using flow file, return static otp_code
        otp_code = "123456"
        return otp_code
        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(self.original_email, self.password)
            mail.select("inbox")
            
            status, messages = mail.search(None, "UNSEEN")
            if status != "OK":
                return None

            email_ids = messages[0].split()[::-1]
            for email_id in email_ids:
                status, msg_data = mail.fetch(email_id, '(RFC822)')
                if status != "OK":
                    print("Failed to fetch email ID:", email_id)
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

        except imaplib.IMAP4.error as e:
            print(f"IMAP error: {e}")
            return None

    def _extract_otp_from_email(self, msg):
        email_body = None
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    email_body = part.get_payload(decode=True).decode()
                    break
        else:
            email_body = msg.get_payload(decode=True).decode()

        if email_body:
            otp_code = self._extract_otp(email_body)
            return otp_code
        return None

    def _extract_otp(self, text):
        match = re.search(r"\b\d{6}\b", text)
        return match.group(0) if match else None

class UserLogin():
    gmail_account_helper = IMAPOTPExtractor(EMAIL, APP_PASSWORD)

    def new_dot_login(self,page, email):
        page.goto(NEWDOT_URL)  
        page.locator('input[type="email"]').fill(email)
        page.wait_for_timeout(2000)
        page.get_by_role("button", name="Continue").nth(0).click()
        page.wait_for_timeout(10000)

        self.gmail_account_helper.set_new_email(email)
        otp = self.gmail_account_helper.check_for_otp()

        if otp:
            page.locator('input[data-testid="validateCode"]').fill(otp)
            # page.get_by_role("button", name="Sign In").click()
        else:
            print("OTP not received.")


def test_verify_workspace_switcher_as_filter():
    with sync_playwright() as p:
        # Launch Chromium browser in visible mode (non-headless)
        browser = p.chromium.launch(headless=False, slow_mo=500, args=[
        "--ignore-certificate-errors", 
        "--disable-web-security",
        "--disable-features=IsolateOrigins,site-per-process"
    ])
        context = browser.new_context(ignore_https_errors=True)
        # Log in user and complete onboarding
        page = context.new_page()
        user = UserLogin()
        user.new_dot_login(page, EMAIL)
        
        #Click on Workspace switcher
        page.get_by_label("Workspaces").click()
        #Check if expensify app icon is not visible on workspace switcher page
        expect(page.locator('.expensify-app-icon_svg__st1').nth(2)).not_to_be_visible()
