import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import imaplib
import email
import re
import random
import time
from typing import Any
from playwright._impl._page import Page
from playwright._impl._browser import Browser
from playwright._impl._locator import Locator
from playwright.sync_api import sync_playwright
from playwright.sync_api._context_manager import PlaywrightContextManager

from utils.trace_cleaner import trace_cleaner

master_email_address = "brighturing926+41510@gmail.com"
master_app_password = "sijknxflhloopmta"


class EmailHandler:
    def __init__(self, email_address, password) -> Any:
        # Validate email and password input
        if not self._validate_email(email_address):
            raise ValueError("Invalid email address format.")
        self.original_email = email_address
        self.password = password

        # Generate new random email using "+" prefix
        random_suffix = random.randint(1000, 9999)
        current_timestamp = int(time.time())
        random_suffix = f"{current_timestamp}{random_suffix}"
        self.new_email = email_address

    def _validate_email(self, email_address) -> Any:
        # Simple email validation
        return bool(re.match(r"[^@]+@[^@]+\.[^@]+", email_address))

    def get_email_address(self) -> Any:
        # Return the generated email with "+" suffix
        return self.new_email

    def check_for_otp(self) -> Any:
        otp_code =  "344095"
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
            return otp_code

        except imaplib.IMAP4.error:
            print("Failed to connect to Gmail. Please check your email address or password.")
            return otp_code

    def _extract_otp_from_email(self, msg) -> Any:
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

    def _extract_otp(self, text) -> Any:
        # Find a 6-digit code in the email body
        match = re.search(r"\b\d{6}\b", text)
        return match.group(0) if match else None


def create_context(p: PlaywrightContextManager) -> tuple[Browser, Any, Page]:
    # Launch chromiun and open new page
    browser = p.chromium.launch(headless=True, args=[
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ],
    )
    context = browser.new_context()
    page: Page = context.new_page()

    # Step 1: Open expensify url
    page.goto('https://dev.new.expensify.com:8082/')

    return browser, context, page


def login_user(page: Page, user_email: str) -> tuple[str, str]:
    # Step 2: Enter email and click continue
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()

    # Magic code entry
    email_handle = EmailHandler(user_email, master_app_password)
    page.wait_for_timeout(5000)
    my_otp_code = email_handle.check_for_otp()
    print(my_otp_code)

    page.get_by_test_id("validateCode").fill(my_otp_code)

    # Step 3: Click join button
    try:
        page.get_by_role("button", name="Sign in").click()

    except Exception:
        pass


def test_assign_to_me() -> None:
    random_num = random.randint(111, 999)
    newWorkspceName = f"mypersonalws{random_num}"
    with sync_playwright() as p:
        browser, context, page = create_context(p)
        context.tracing.start(screenshots=True, snapshots=True, sources=True)

        try:
            # Step 1: Login user
            login_user(page, master_email_address)

            page.get_by_label("Inbox").click()
            page.get_by_role("button", name="Create").click()
            page.get_by_text("Assign task").click()
            page.get_by_role("textbox", name="Title").fill("Doing Things")
            page.get_by_role("button", name="Next").click()
            page.get_by_text("Assignee").click()

            assign_to_me = page.get_by_text("Assign to me")

            page.wait_for_timeout(1000)

            assert assign_to_me.is_visible(), "Assign to me is not visible"

        except Exception as e:
            print(f"Test failed: {e}")
            raise e
        finally:
            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            browser.close()


def create_new_workspace(page: Page, ws_name: str, first_name: str, last_name: str) -> str:
    """Create a new workspace"""
    random_num = random.randint(111, 999)
    new_workspace_name = f"{ws_name}{random_num}"
    page.get_by_label("New workspace").click()
    new_created_ws1 = get_newly_created_ws(page, first_name, last_name)

    new_created_ws1.click()
    page.get_by_role("textbox", name="Name").click()
    page.get_by_role("textbox", name="Name").fill(new_workspace_name)
    page.wait_for_timeout(1000)
    page.get_by_role("button", name="Save").click()
    page.wait_for_timeout(1000)
    # page.get_by_label("Back").click()
    return new_workspace_name


def get_newly_created_ws(page: Page, first_name: str, last_name: str) -> Locator | None:
    """
    Check for the latest created workspace to be used for testing
    """
    buttons = page.get_by_test_id("WorkspacePageWithSections").locator(f"text={first_name} {last_name}'s Workspace")
    button_count = buttons.count()

    latest_button = None
    max_number = -1
    for i in range(button_count):
        button_text = buttons.nth(i).inner_text()
        # Find the number at the end of the button text using regex
        match = re.search(r"\d+$", button_text)
        if match:
            number = int(match.group())
            if number > max_number:
                max_number = number
                latest_button = buttons.nth(i)

    if latest_button:
        return latest_button
    else:
        print("No button with a numeric suffix found.")


def get_names_for_existing_account(page: Page) -> tuple[str, str]:
    """
    Retrive first and last name from the account profile
    """
    page.get_by_label("My settings").click()
    try:
        page.get_by_label("Close").click(timeout=1000)
    except Exception:
        pass
    page.get_by_role("menuitem", name="Profile").click()
    page.get_by_text("Display name").click()
    f_name = page.get_by_role("textbox", name="First name")
    l_name = page.get_by_role("textbox", name="Last name")
    page.wait_for_timeout(2000)
    # page.keyboard.down("Escape")
    page.get_by_label("Back").click()

    return f_name.input_value(), l_name.input_value()