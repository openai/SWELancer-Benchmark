import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import email
import imaplib
import re
from imaplib import IMAP4_SSL

import pytest
from playwright.sync_api import Page, expect, sync_playwright

from utils.trace_cleaner import trace_cleaner

# Email
BASE_EMAIL = "testerfreelancer555+49894@gmail.com"
PASSWORD = "snct ajbr yadx kwlq"


class EmailHandler:
    def __init__(self, email_address, password):
        # Validate email and password input
        if not self._validate_email(email_address):
            raise ValueError("Invalid email address format.")
        self.original_email = email_address
        self.password = password

    def _validate_email(self, email_address):
        # Simple email validation
        return bool(re.match(r"[^@]+@[^@]+\.[^@]+", email_address))

    def get_email_address(self):
        # Return the generated email with "+" suffix
        return self.original_email

    def check_for_otp(self, page, target=False, cached=False):
        if cached:
            return "123456"
        # Connect to the Gmail server using IMAP
        if not target:
            target = self.original_email
        try:
            tries = 1
            limit_tries = 5
            while tries <= limit_tries:
                mail = imaplib.IMAP4_SSL("imap.gmail.com")
                mail.login(self.original_email, self.password)
                mail.select("inbox")

                # Fetch all unread emails
                status, messages = mail.search(None, "UNSEEN")
                if status != "OK":
                    print("No unread emails found.")

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
                            if msg["To"] == target:
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
                tries += 1
                page.wait_for_timeout(1000)

            # Logout if OTP not found in unread emails
            if isinstance(mail, IMAP4_SSL):
                mail.close()
                mail.logout()
            print("No OTP found in unread emails.")
            return None

        except imaplib.IMAP4.error as error:
            print(error)
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

    def clear_inbox(self):
        """
        Delete all existing messages from the Inbox.
        """
        print("Deleting all existing messages from the email inbox")
        with imaplib.IMAP4_SSL(host="imap.gmail.com") as imap:
            imap.login(self.original_email, self.password)
            imap.select("inbox")
            imap.store("1:*", "+FLAGS", "\\Deleted")
            imap.expunge()
            imap.close()


@pytest.fixture
def setup_playwright():
    # Initialize Playwright and browser setup
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(
        headless=True,
        args=[
            "--ignore-certificate-errors",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
        ],
    )
    page = browser.new_page()
    yield page, browser  # Yield the page object to the test function
    browser.close()
    playwright.stop()


# Function to log in to the application
def login_user(page: Page, account: EmailHandler, cached=False):
    # Open Expensify URL and log in
    user_email = account.get_email_address()
    page.goto("https://dev.new.expensify.com:8082/")
    # Clearing the inbox before asking for the magic code
    account.clear_inbox()
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()

    try:
        expect(page.get_by_role("button", name="Sign in")).to_be_visible()
        page.get_by_test_id("validateCode").fill(
            account.check_for_otp(page, cached=cached)
        )
    except Exception as error:
        print(error)


@pytest.mark.parametrize("first_name, last_name", [("Test_1", "User_1")])
def test_markdown(setup_playwright, first_name, last_name):
    page, browser = setup_playwright
    # Start tracing
    page.context.tracing.start(screenshots=True, snapshots=True, sources=True)
    trace_file = "/app/expensify/user_tool/output_browser1.zip"

    try:
        account = EmailHandler(email_address=BASE_EMAIL, password=PASSWORD)
        cached = True

        # Log in as the user
        login_user(page, account, cached)

        user_1 = "testerfreelancer555+1@gmail.com"
        # Creating a group chat with another user
        page.get_by_label("Start chat (Floating action)").click()
        page.get_by_text("Start chat").click()
        page.get_by_test_id("selection-list-text-input").fill(user_1)
        page.get_by_label(user_1).get_by_role("button", name="Add to group").click()
        page.get_by_role("button", name="Next").click()
        page.get_by_role("button", name="Start group").click()
        # Creating a new task
        page.get_by_label("Create").last.click()
        page.get_by_text("Assign task").click()
        page.get_by_role("textbox", name="Title").fill("Task")
        page.get_by_role("button", name="Next").click()
        # Updating the task description to test the markdown code block
        page.get_by_test_id("NewTaskPage").get_by_text("Description").click()
        page.get_by_role("textbox", name="Description (optional)").fill("` ` ")
        page.get_by_role("button", name="Next").click()
        expect(page.get_by_test_id("comment").get_by_text("``")).not_to_be_visible()

    except Exception as e:
        print(f"Test encountered an error: {str(e)}")
        raise e
    finally:
        # Stop tracing and export
        page.context.tracing.stop()
        page.context.tracing.export_to_file(trace_file)
        trace_cleaner(trace_file)
