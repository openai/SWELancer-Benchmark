import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import imaplib
import email
import re
import random
import time
from typing import Any
from playwright.sync_api import sync_playwright
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page

from utils.trace_cleaner import trace_cleaner

master_email_address = "brighturing926+49933@gmail.com"
master_app_password = "sijknxflhloopmta"
dev_base_url = "https://dev.new.expensify.com:8082"
first_user = "brighturing926+33@gmail.com"
second_user = "brighturing926+31@gmail.com"
first_user_fname, first_user_lname = "Miriam", "Korsa"
second_user_fname, second_user_lname = "Aku", "Nicole"


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


def login_user(p: PlaywrightContextManager, user_email: str) -> tuple[Browser, Page]:
    # Launch chromiun and open new page
    browser = p.chromium.launch(channel="chrome", headless=True, args=[
        "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"])
    context = browser.new_context()
    page: Page = context.new_page()

    # Step 1: Open expensify url
    page.goto(dev_base_url)

    # Step 2: Enter email and click continue
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()

    # Magic code entry
    email_handle = EmailHandler(user_email, master_app_password)
    page.wait_for_timeout(5000)
    my_otp_code = email_handle.check_for_otp()

    try:
        page.get_by_test_id("validateCode").fill(my_otp_code)
    except:
        page.locator('input[data-testid="validateCode"]').fill("123456")

    # Step 3: Click join button
    try:
        page.get_by_role("button", name="Sign in").click()
    except Exception:
        pass

    return browser, page


def test_welcome_message_group_chat() -> None:
    with sync_playwright() as p:
        browser, page = login_user(p, master_email_address)
        context = page.context
        trace_path = "/app/expensify/user_tool/output_browser1.zip"
        context.tracing.start(screenshots=True, snapshots=True, sources=True)

        try:
            first_name, last_name = get_names_for_existing_account(page)

            page.wait_for_timeout(3000)
            page.get_by_label("Start chat (Floating action)").click()
            page.get_by_label("Start chat", exact=True).click()
            page.get_by_test_id("selection-list-text-input").fill(first_user)
            page.wait_for_timeout(3000)
            page.get_by_role("button", name="Add to group").click()
            page.get_by_test_id("selection-list-text-input").fill(second_user)
            page.wait_for_timeout(3000)
            page.get_by_role("button", name="Add to group").click()
            page.get_by_role("button", name="Next").click()
            page.get_by_role("button", name="Start group").click()

            page.wait_for_timeout(3000)

            user_name_list: list[str] = sorted([first_name, first_user_fname, second_user_fname])
            page.locator('button[aria-label="Navigates to a chat"]', has_text=", ".join(user_name_list)).first.click()
            page.get_by_label(", ".join(user_name_list), exact=True).first.click()
            page.get_by_label("Members").click()
            page.get_by_text(f"{first_user_fname} {first_user_lname}").last.click()
            page.get_by_role("button", name="Remove from group").click()
            page.get_by_role("button", name="Remove", exact=True).click()
            page.locator("#overLayBottomButton").click()
            page.wait_for_timeout(3000)

            welcome_msg = page.locator("div[class^='css-text-']", has_text=f"This chat is with {second_user_fname} {second_user_lname}").first

            assert welcome_msg.is_visible(), "Deleted user exists in welcome message"

            remaining_users = sorted([first_name, second_user_fname])
            page.get_by_label(", ".join(remaining_users)).last.click()
            page.get_by_label("Leave").click()
            page.wait_for_timeout(1000)

        except Exception as e:
            # Optionally log the error or re-raise
            raise e
        finally:
            context.tracing.stop(path=trace_path)
            trace_cleaner(trace_path)
            browser.close()


def get_names_for_existing_account(page: Page) -> tuple[str, str]:
    """
    Retrive first and last name from the account profile
    """
    page.get_by_label("My settings").click()
    page.wait_for_timeout(2000)
    page.get_by_role("menuitem", name="Profile").click()
    page.get_by_text("Display name").click()
    f_name = page.get_by_role("textbox", name="First name")
    l_name = page.get_by_role("textbox", name="Last name")
    page.wait_for_timeout(2000)
    page.keyboard.down("Escape")

    return f_name.input_value(), l_name.input_value()