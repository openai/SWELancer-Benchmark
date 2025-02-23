import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import email
import imaplib
import re
import time
import pytest
import random
from playwright.sync_api import sync_playwright, Page
from utils.trace_cleaner import trace_cleaner  # <--- Added import


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


gmail_account_helper = IMAPOTPExtractor(EMAIL, PASSWORD)


@pytest.fixture
def setup_playwright(request):
    width = getattr(request, "param", {}).get("width", 1280)
    height = getattr(request, "param", {}).get("height", 720)

    playwright = sync_playwright().start()

    browser = playwright.chromium.launch(
        headless=True, args=[
            "--ignore-certificate-errors",
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process'
        ])

    context = browser.new_context(viewport={"width": width, "height": height}, timezone_id="Europe/Bucharest")

    context.tracing.start(screenshots=True, snapshots=True, sources=True)

    page = context.new_page()

    yield page, context


    browser.close()
    playwright.stop()


def login_user(page: Page, email: str):
    page.goto("https://dev.new.expensify.com:8082/")
    page.locator('input[type="email"]').fill(email)
    page.locator('button[tabindex="0"]').click()
    time.sleep(1)


    otp = "123456"
    page.locator('input[data-testid="validateCode"]').fill(otp)


@pytest.mark.parametrize(
    "setup_playwright",
    [{"width": 1280, "height": 720}],
    indirect=True,
)
def test(setup_playwright):
    page, context = setup_playwright
    try:
        email = EMAIL
        login_user(page, email)


        page.locator(
            'button[aria-label="Start chat (Floating action)"][tabindex="0"]'
        ).click()


        page.locator('div[aria-label="Start chat"][role="menuitem"]').click()


        for i in range(3):
            email = f"example_{i}_{int(time.time())}@gmail.com"

            input_field = page.locator('input[data-testid="selection-list-text-input"]')
            input_field.fill(email)
            time.sleep(1)
            page.get_by_role("button", name="Add to group").click()


        page.wait_for_timeout(3000)
        page.keyboard.press("Enter")
        page.wait_for_timeout(3000)
        page.keyboard.press("Enter")
        page.wait_for_timeout(4000)
        page.locator('button[aria-label="Create"]').last.click()
        page.locator('div[aria-label="Split expense"]').click()
        page.locator('button[aria-label="Manual"]').last.click()
        page.locator('input[role="presentation"]').fill("1000")
        page.wait_for_timeout(3000)
        page.keyboard.press("Enter")
        page.wait_for_timeout(3000)
        page.keyboard.press("Enter")

        split_text = page.locator('div[aria-label="Split"]').inner_text()
        print(split_text)
        assert (
            ("(none)" not in split_text)
            and (f"testuser{i}@gmail.com" not in split_text)
        )
    finally:

        trace_path = "/app/expensify/user_tool/output_browser1.zip"
        context.tracing.stop(path=trace_path)
        trace_cleaner(trace_path)
