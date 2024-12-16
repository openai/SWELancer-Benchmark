import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
import pytest
import random
from playwright.sync_api import sync_playwright, Page
import imaplib
import email
import re

from utils.trace_cleaner import trace_cleaner

email_address = "t56826807+10@gmail.com"
password = "wxck tsaw ocna tkfd"


class EmailHandler:
    def __init__(self, email_address=email_address, password=password):
        if not self._validate_email(email_address):
            raise ValueError("Invalid email address format.")
        self.original_email = email_address
        self.password = password

        random_suffix = random.randint(1000, 9999)
        current_timestamp = int(time.time())
        random_suffix = f"{current_timestamp}{random_suffix}"
        self.new_email = self._generate_new_email(email_address, random_suffix)

    def _validate_email(self, email_address):
        return bool(re.match(r"[^@]+@[^@]+\.[^@]+", email_address))

    def _generate_new_email(self, email_address, suffix):
        username, domain = email_address.split("@")
        # return f"{username}+{suffix}@{domain}"
        return email_address

    def get_email_address(self):
        return self.new_email

    def check_for_otp(self, recipient: str = None, retries=5, delay=5):
        """
        Check for OTP in the Gmail inbox.
        """
        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(self.original_email, self.password)

            for _ in range(retries):
                mail.select("inbox")
                status, messages = mail.search(None, '(UNSEEN SUBJECT "Expensify magic sign-in code:")')

                if status == "OK":
                    email_ids = messages[0].split()
                    if email_ids:
                        latest_email_id = email_ids[-1]
                        status, msg_data = mail.fetch(latest_email_id, "(RFC822)")

                        for response_part in msg_data:
                            if isinstance(response_part, tuple):
                                msg = email.message_from_bytes(response_part[1])

                                if recipient and msg["To"] != recipient:
                                    continue

                                otp_code = self._extract_otp_from_email(msg)
                                if otp_code:
                                    mail.store(latest_email_id, "+FLAGS", "\\Deleted")
                                    mail.expunge()
                                    mail.close()
                                    mail.logout()
                                    return otp_code

            mail.close()
            mail.logout()
            print("Max retries reached. No OTP found.")
            return None

        except imaplib.IMAP4.error as e:
            print(f"Failed to connect to Gmail: {e}")
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


email_client = EmailHandler()


@pytest.fixture
def setup_playwright():
    playwright = sync_playwright().start()

    browser_user1 = playwright.chromium.launch(
        headless=True,
        slow_mo=1000,
        args=[
            "--ignore-certificate-errors",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
        ],
    )
    # Use a context to enable tracing
    context_user1 = browser_user1.new_context()
    page_user1 = context_user1.new_page()

    yield page_user1

    context_user1.close()
    playwright.stop()


def login_user(page: Page, email: str):
    page.goto("https://dev.new.expensify.com:8082/")
    page.locator('input[type="email"]').fill(email)
    page.locator('button[tabindex="0"]').click()

    page.locator('input[name="validateCode"]').fill("123456")


def complete_onboarding(page: Page, name: str):
    page.locator("text='Track and budget expenses'").click()
    page.locator('input[name="fname"]').fill(name)
    page.locator('input[name="lname"]').fill("")
    page.get_by_role("button", name="Continue").last.click()


@pytest.mark.parametrize(
    "setup_playwright",
    [{"width": 1280, "height": 720}],
    indirect=True,
)

def test(setup_playwright):
    page = setup_playwright
    context = page.context
    trace_path = "/app/expensify/user_tool/output_browser1.zip"

    # Start recording the trace
    context.tracing.start(screenshots=True, snapshots=True, sources=True)

    try:
        client = EmailHandler()
        email = client.get_email_address()
        login_user(page, email)

        # complete_onboarding(page, "Test User")

        page.locator('button[aria-label="Workspaces"]').click()
        page.get_by_test_id("WorkspaceSwitcherPage").get_by_role(
            "button", name="New workspace"
        ).click()
        page.locator('div[aria-label="More features"]').last.click()
        page.locator(
            'button[aria-label="Classify costs and track billable expenses."]'
        ).last.click()
        page.locator('div[aria-label="Tags"]').last.click()
        page.locator("button", has_text="Add tag").last.click()
        page.locator('input[aria-label="Name"]').last.fill("abc")
        page.locator('button[data-listener="Enter"]', has_text="Save").last.click()

        page.locator('div[aria-label="Select all"]').last.click()
        page.locator("button", has_text="1 selected").last.click()
        page.locator('div[aria-label="Delete tag"]').last.click()
        page.locator('button[data-listener="Enter"]', has_text="Delete").last.click()

        visible = page.locator(
            'div[dir="auto"]', has_text="You haven't created any tags"
        ).is_visible()

        assert visible, "Blank screen after deleting all tags!"

    except Exception as e:
        # Stop the trace on failure and clean it
        context.tracing.stop(path=trace_path)
        trace_cleaner(trace_path)
        raise e
    else:
        # Stop the trace on success and clean it
        context.tracing.stop(path=trace_path)
        trace_cleaner(trace_path)
