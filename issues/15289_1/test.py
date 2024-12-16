import re
import logging
import imaplib
import email
from playwright.sync_api import Page, expect, sync_playwright

EMAIL = "velmoner+960@gmail.com"
PASSWORD = "aory ezrb qkmi qkas"
NEWDOT_URL = "https://dev.new.expensify.com:8082/"
first_name = "aa"
last_name = "bb"


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
    def get_otp(email_id: str, password: str) -> str:
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


def user_login(page: str, email_id: str):
    page.goto(NEWDOT_URL)

    page.locator('input[type="email"]').fill(email_id)
    page.wait_for_timeout(2000)
    page.get_by_role("button", name="Continue").nth(0).click()
    # page.wait_for_timeout(10000)

    otp = "123456"  # OTPUtil.get_otp(email_id=EMAIL, password=PASSWORD)

    page.locator('input[data-testid="validateCode"]').fill(otp)
    try:
        page.get_by_role("button", name="Sign In").click()
    except Exception as err:
        pass


def test_expensify_15289():
    with sync_playwright() as p:
        browser = p.chromium.launch(proxy={"server": "http://localhost:8080"}, headless=False, args=[
                                    "--no-sandbox", "--disable-dev-shm-usage", "--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"], slow_mo=None, channel="chromium")
        context = browser.new_context()
        page = context.new_page()
        page.goto(NEWDOT_URL)
        user_login(page=page, email_id=EMAIL)
        page.wait_for_timeout(2000)

        page.get_by_text(f"{first_name} {last_name} (you)").click(
            button="right")
        page.wait_for_timeout(500)

        try:
            assert page.get_by_label("Unpin").is_visible()
        except Exception as err:
            logging.error(
                "report's context popover menu didn't open: assertion failed")

        page.mouse.click(x=0, y=0, button="right")
        page.wait_for_timeout(900)

        assert not page.get_by_label("Unpin").is_visible()

        context.close()
        browser.close()
