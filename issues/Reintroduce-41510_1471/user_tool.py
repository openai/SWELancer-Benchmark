import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import imaplib
import email
import re
from playwright.sync_api import sync_playwright, expect
from utils.trace_cleaner import trace_cleaner

EMAIL = "velmoner+960@gmail.com"
PASSWORD = "aory ezrb qkmi qkas"
NEWDOT_URL = "https://dev.new.expensify.com:8082/"

class OTPUtil:
    @staticmethod
    def _parse_otp(text):
        match = re.search(r"\b\d{6}\b", text)
        return match.group(0) if match else None

    @staticmethod
    def _fetch_otp(msg) -> str:
        otp = None
        if not msg.is_multipart():
            body = msg.get_payload(
                decode=True).decode()
            otp = OTPUtil._parse_otp(body)
            if otp:
                return otp
        
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                _body = part.get_payload(
                    decode=True).decode()
                otp = OTPUtil._parse_otp(_body)
        if otp:
            return otp

    @staticmethod
    def get_otp(email_id:str, password:str) -> str:
        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(email_id, password)
            mail.select("inbox")
            
            status, messages = mail.search(None, "UNSEEN")
            if status != "OK":
                return None

            emails = messages[0].split()[::-1]

            for id in emails:
                status, msg_data = mail.fetch(
                    id, '(RFC822)')
                if status != "OK":
                    continue

                for resp in msg_data:
                    if isinstance(resp, tuple):
                        msg = email.message_from_bytes(resp[1])

                        if email_id in msg["To"]:
                            otp_code = OTPUtil._fetch_otp(msg)
                            if otp_code:
                                mail.store(id, '+FLAGS', '\\Deleted')
                                mail.expunge()
                                mail.close()
                                mail.logout()
                                return otp_code
        
            mail.close()
            mail.logout()
            return None

        except imaplib.IMAP4.error:
            return None

def user_login(page:str, email_id:str):
    page.goto(NEWDOT_URL)
    page.locator('input[type="email"]').fill(email_id)
    page.wait_for_timeout(2000)
    page.get_by_role("button", name="Continue").nth(0).click()
    page.wait_for_timeout(10000)

    #otp = OTPUtil.get_otp(email_id=EMAIL, password=PASSWORD)
    otp = "123456"
    page.locator('input[data-testid="validateCode"]').fill(otp)
    try:
        page.get_by_role("button", name="Sign In").click()
    except Exception as err:
        pass


def test_payment_text():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="chrome",
            headless=True,
            args=[
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process"
            ]
        )

        context = browser.new_context()
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        page = context.new_page()

        try:
            user_login(page=page, email_id=EMAIL)
            
            # Step 2: create task to asign
            page.get_by_label("Start chat (Floating action)").click()
            page.get_by_label("Assign task").click()

            # Step 3: Enter the test task
            page.get_by_role("textbox", name="Title").fill("test task")
            page.get_by_role("textbox", name="Title").press("Enter")
            page.wait_for_timeout(2000)

            # Step 4: Select assignee and check if the test assign to me is visible
            page.get_by_role("menuitem", name="Assignee").click()
            page.wait_for_timeout(2000)
            expect(page.get_by_text("Assign to me")).to_be_visible()
        except Exception as ex:
            print(f"Test failed with error: {ex}")
        finally:
            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            browser.close()
