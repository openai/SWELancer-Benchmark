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
import os

from utils.trace_cleaner import trace_cleaner  # <--- ADDED

email_address = "rgulraiz2000@gmail.com"
password = "kepw uquj myoa npvj"

class EmailHandler:
    def __init__(self, email_address=email_address, password=password):
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
        username, domain = email_address.split("@")
        return f"{username}+{112211}@{domain}"

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
                                mail.store(email_id, "+FLAGS", "\\Deleted")
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

@pytest.fixture
def setup_playwright(request):
    width = getattr(request, "param", {}).get("width", 1280)
    height = getattr(request, "param", {}).get("height", 720)

    playwright = sync_playwright().start()

    browser = playwright.chromium.launch(
        channel="chrome",
        headless=True,
        args=[
                "--ignore-certificate-errors",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process"
            ],
            proxy={"server": "http://localhost:8080"},
            slow_mo=500
    )

    context = browser.new_context(viewport={"width": width, "height": height})
    page = context.new_page()

    yield page, context

    # Cleanup
    browser.close()
    playwright.stop()


def login_user(page: Page, email: str, client):
    page.goto("https://dev.new.expensify.com:8082/")
    page.wait_for_timeout(5000)

    page.locator('input[type="email"]').fill(email)
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(2000)
    try:
        join_button = page.get_by_role("button", name="Join")
        if (join_button.is_visible()):
            join_button.click(timeout=3000)
        else:
            validate_code_input = page.locator('input[data-testid="validateCode"]')
            validate_code_input = page.locator('input[name="validateCode"]')
            validate_code_input = page.locator('input[autocomplete="one-time-code"][maxlength="6"]')
            # magic_code = client.check_for_otp()
            magic_code = "010101"
            validate_code_input.fill(magic_code)
    except Exception:
        pass


def submit_scan_expense_es(page, receipt_path):
    with page.expect_file_chooser() as fc_info:
        action_button = page.locator('button[aria-label="Iniciar chat (Acción flotante)"]')
        if action_button.count() > 1:
            action_button.last.click()
        else:
            action_button.click()
        page.locator('div[aria-label="Seguimiento de gastos"]').click()

        try:
            page.locator(
                'button[data-listener="Enter"]', has_text="Ok, entendido"
            ).click(timeout=2000)
        except Exception:
            pass

        page.locator('button[aria-label="Escanear"]').click()
        page.locator('button[aria-label="Elegir archivo"]').click()

    file_chooser = fc_info.value
    file_chooser.set_files(receipt_path)

    page.locator(
        'button[data-listener="Enter"]', has_text="Seguimiento de gastos"
    ).click()

    try:
        page.locator("button", has_text="Ahora no").click(timeout=2000)
    except Exception:
        pass

@pytest.mark.parametrize(
    "setup_playwright",
    [{"width": 1280, "height": 720}],
    indirect=True,
)
def test(setup_playwright):
    page, context = setup_playwright
    # Start tracing
    context.tracing.start(title="test_trace", screenshots=True, snapshots=True)

    trace_path = "/app/expensify/user_tool/output_browser1.zip"  # <--- where we'll export the trace

    try:
        # Submit a scan expense here
        receipt_path = os.path.expanduser(
            "C:/TestCases/resturant bill.jpg"  # Add your local file path here
        )

        client = EmailHandler()
        email = client.get_email_address()

        login_user(page, email, client)
        page.wait_for_timeout(5000)

        # Enter user details and complete onboarding\
        if page.get_by_text("Track and budget expenses").is_visible():
            page.locator("text='Track and budget expenses'").click()
            page.locator('input[name="fname"]').fill("Test")
            page.locator('input[name="lname"]').fill("User")
            page.get_by_role("button", name="Continue").last.click()

        # Change language to Spanish
        page.locator('button[aria-label="My settings"]').click()
        page.locator('div[aria-label="Preferences"]').click()
        page.locator('div[aria-label="English"]').click()
        page.locator('button[aria-label="Spanish"]').click()

        submit_scan_expense_es(page, receipt_path)

        # Click on the latest expense details
        page.locator('div[aria-label="Efectivo"]').last.click()

        # Edit amount
        page.locator(
            'div[data-tag="pressable"]', has_text="Importe • Efectivo"
        ).last.click()
        page.locator('input[type="text"]').last.fill("1000")
        page.locator('button[data-listener="Enter"]', has_text="Guardar").last.click()

        # Grab the text from chat
        chat_text = page.locator('div[aria-label="mensaje de chat"]').last.inner_text()

        assert "estableció la importe" not in chat_text

    finally:
        # Stop tracing and export
        context.tracing.stop()
        context.tracing.export(path=trace_path)
        # Clean the trace
        trace_cleaner(trace_path)
