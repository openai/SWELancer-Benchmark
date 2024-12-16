import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import re
import time
import email
import pytest
import random
import imaplib
from playwright._impl._page import Page
from playwright.sync_api import sync_playwright, expect

# Email
BASE_EMAIL = "testerfreelancer555+28943@gmail.com"
PASSWORD = "snct ajbr yadx kwlq"


class EmailHandler:
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
        username, domain = "testerfreelancer@gmail.com".split('@')
        return f"{username}+{suffix}@{domain}"

    def get_new_email_address(self):
        # Return the generated email with "+" suffix
        return self.new_email

    def get_email_address(self):
        # Return the generated email with "+" suffix
        return self.original_email

    def check_for_otp(self, page, target=False):
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
                    status, msg_data = mail.fetch(email_id, '(RFC822)')
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
                                    mail.store(email_id, '+FLAGS', '\\Deleted')
                                    mail.expunge()  # Permanently removes deleted emails from the mailbox

                                    # Logout and return OTP
                                    mail.close()
                                    mail.logout()
                                    return otp_code
                tries += 1
                page.wait_for_timeout(1000)

            # Logout if OTP not found in unread emails
            mail.close()
            mail.logout()
            print("No OTP found in unread emails.")
            return None

        except imaplib.IMAP4.error as error:
            print(error)
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
        headless=True, args=["--ignore-certificate-errors", '--disable-web-security',
        '--disable-features=IsolateOrigins,site-per-process']
    )
    context = browser.new_context()
    yield context  # Yield the page object to the test function
    browser.close()
    playwright.stop()


# Function to log in to the application
def login_user(page: Page, account: EmailHandler):
    # Open Expensify URL and log in
    user_email = account.get_email_address()
    page.goto("https://dev.new.expensify.com:8082/")
    account.clear_inbox()
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()

    try:
        expect(page.get_by_role("button", name="Sign in")).to_be_visible()
        page.get_by_test_id("validateCode").fill("123456")
    except Exception as error:
        print(error)
        page.get_by_role("button", name="Join").click()


def create_a_new_workspace(page):
    # Going to the settings page
    page.get_by_label("My settings").click()
    # Accessing the workspace's page
    page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").get_by_text("Workspaces").click()
    # Creating a new workspace
    page.wait_for_timeout(
        3000)  # Waiting the page to load because the loading page has two buttons which might cause an exception because none of them work
    try:
        page.get_by_label("New workspace").click()
    except:
        page.get_by_label("New workspace").first.click()  # In case there is no workspace yet

    try:
        return page.get_by_label("Test User's Workspace").inner_text().split('\n')[1]
    except:
        return page.get_by_label("Test User's Workspace").last.inner_text().split('\n')[1]


def access_target_workspace_chat(page, chat_name):
    page.get_by_label("Back").first.click()
    page.get_by_label("Inbox").click()
    try:
        expect(page.locator("#root")).not_to_contain_text("Say hello!")
        expect(page.get_by_label("Chat welcome message")).not_to_contain_text("Welcome to #admins!")
        page.get_by_test_id("DisplayNamesWithTooltip").filter(has_text=re.compile(rf"^{chat_name}$")).last.click()
    except:
        page.get_by_test_id("DisplayNamesWithTooltip").filter(has_text=re.compile(rf"^{chat_name}$")).first.click()


def submit_invalid_expense(page):
    page.get_by_label("Create").last.click()
    page.get_by_text("Submit expense", exact=True).click()
    page.get_by_label("Distance").click()
    page.get_by_test_id("IOURequestStartPage").get_by_role("button", name="Start").click()
    page.get_by_test_id("IOURequestStepWaypoint").get_by_role("textbox").fill("abc")  # Inputting invalid location
    page.get_by_role("button", name="Save").click()
    page.get_by_role("button", name="Stop").click()
    page.get_by_test_id("IOURequestStepWaypoint").get_by_role("textbox").fill("def")  # Inputting invalid location
    page.get_by_role("button", name="Save").click()
    page.get_by_role("button", name="Next").nth(1).click()
    page.get_by_role("button", name="Submit expense").click()


@pytest.mark.parametrize("first_name, last_name", [("Test", "User")])
def test_selected_highlight(setup_playwright, first_name, last_name):
    context = setup_playwright
    account = EmailHandler(email_address=BASE_EMAIL, password=PASSWORD)
    user_email = account.get_email_address()

    # Log in as the user
    page = context.new_page()
    login_user(page, account)

    # Creating a new workspace
    workspace_name = create_a_new_workspace(page)

    # Acessing the workspace chat
    access_target_workspace_chat(page, workspace_name)

    # Clicking on the chat header
    page.get_by_label("Test User's Workspace").click()
    # Accessing the chat settings
    page.get_by_test_id("ReportDetailsPage").get_by_text("Settings").click()
    # Accessing the notification options
    page.get_by_text("Notify me about new messages").click()
    selected_option = page.get_by_test_id("selection-list").get_by_label("Immediately")
    expect(selected_option).to_have_css("background-color", "rgba(0, 0, 0, 0)")
