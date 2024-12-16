import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import expect
from playwright.sync_api._context_manager import Playwright
from playwright._impl._page import Page
import email
import imaplib
import random
import re
import time
from playwright.sync_api import sync_playwright

from utils.trace_cleaner import trace_cleaner

# Constants for URLs and credentials
NEWDOT_URL = "https://dev.new.expensify.com:8082/"
EMAIL = "ikhanle001@gmail.com"
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


# Initialize the OTP extractor
gmail_account_helper = IMAPOTPExtractor(EMAIL, PASSWORD)

def login_user(p: Playwright):
    # Launch chromium and open new page
    galaxy_s8 = p.devices['Galaxy S8']
    browser = p.chromium.launch(headless=True, args=[
        "--disable-web-security",
        "--disable-features=IsolateOrigins,site-per-process",
        "--ignore-certificate-errors"
    ])
    context = browser.new_context(
        **galaxy_s8
    )
    page = context.new_page()

    user_email = EMAIL

    # Step 1: Open expensify url
    page.goto('https://dev.new.expensify.com:8082/')

    page.locator('input[type="email"]').fill(user_email)
    page.wait_for_timeout(2000)
    page.get_by_role("button", name="Continue").nth(0).click()
    page.wait_for_timeout(2000)
    gmail_account_helper.set_new_email(user_email)

    try:
        expect(page.get_by_test_id("SignInPage").get_by_test_id("validateCode")).to_be_visible(timeout=5000)
    except (AssertionError, TimeoutError):
        # If not required, expect the join button to appear and click the button
        page.get_by_test_id("SignInPage").get_by_role("button", name="Join").click()
    else:
        otp = "123456" # gmail_account_helper.check_for_otp()
        page.locator('input[data-testid="validateCode"]').fill(otp)

    # Check if onboarding is required
    try:
        expect(page.get_by_text("What do you want to do today?")).to_be_visible(timeout=5000)
    except (AssertionError, TimeoutError):
        pass
    else:
        # Complete the onboarding
        page.get_by_label("Track and budget expenses").click()
        page.get_by_role("textbox", name="First name").fill("Milan")
        page.get_by_role("textbox", name="Last name").fill("T")
        page.get_by_role("button", name="Continue").click()

    return browser, context, page, user_email

def create_group_chat(page: Page, users):
    div_get_started_here = page.locator('div:has-text("Get started here!")')
    if div_get_started_here.count() > 0:
        page.locator('button[aria-label="Close"]').last.click()

    # Steps to add multiple users to the group
    for user in users:
        email = user
        # Fill in the email field and click "Add to group"
        input_field = page.locator('input[data-testid="selection-list-text-input"]')
        input_field.fill(email)
        page.wait_for_timeout(1000)
        page.locator('button:has(div:text("Add to group"))').nth(1).click()
        page.wait_for_timeout(1000)

    # Confirm the selection and open the members list
    input_field.press("Enter")
    page.wait_for_timeout(1000)
    page.locator('div[data-testid="selection-list"]').nth(1).press("Enter")
    page.wait_for_timeout(1000)

def delete_user_from_group(page: Page):
    details = page.locator('button[aria-label="Details"]')
    expect(details).to_be_visible()
    details.click()

    all_members = page.locator('div[aria-label="Members"]')
    expect(all_members).to_be_visible()
    all_members.click()

    # select last user to remove from group
    selection_list = page.locator('div[data-testid="selection-list"]')
    delete_last_user = selection_list.locator('button[role="button"]').last
    expect(delete_last_user).to_be_visible()
    delete_last_user.click()

    remove_from_group = page.locator('button[role="button"]', has_text='Remove from group')
    expect(remove_from_group).to_be_visible()
    remove_from_group.click()

    # delete the last user successfully
    confirm_delete = page.locator('button[data-listener="Enter"]', has_text='Remove')
    expect(confirm_delete).to_be_visible()
    confirm_delete.click()

    # Navigate back to group chat
    back_btn_1 = page.locator('button[aria-label="Back"]').last
    expect(back_btn_1).to_be_visible()
    back_btn_1.click()

    # Navigate back to group chat
    back_btn_2 = page.locator('button[aria-label="Back"]').last
    expect(back_btn_2).to_be_visible()
    back_btn_2.click()

def test_welcome_group_message():
    with sync_playwright() as p:
        # Login and get context
        browser, context, page, user_email = login_user(p)

        # Start the trace
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        trace_path = "/app/expensify/user_tool/output_browser1.zip"

        try:
            users = [f"user.{i}.{int(time.time())}@example.com" for i in range(3)]

            # Step 2: Click on + icon and click on "Start chat"
            try:
                locator = page.locator("button[aria-label='Back'][role='button']").first
                locator.click(timeout=2000)
            except:
                pass

            plus_icon = page.locator('button[aria-label="Start chat (Floating action)"]')
            expect(plus_icon).to_be_visible()
            plus_icon.focus()
            # Call click two times because Close button blocking click action in the first try
            plus_icon.click(force=True, timeout=2000)
            plus_icon.click(force=True, timeout=2000)
            page.wait_for_timeout(2000)

            start_chat = page.locator('div[aria-label="Start chat"]')
            expect(start_chat).to_be_visible()
            start_chat.click()
            page.wait_for_timeout(2000)

            # Step 3: Create group chat with 3 users
            create_group_chat(page, users)

            # Step 4: Delete one user from the group
            delete_user_from_group(page)

            # Step 5: check if user email is displayed in welcome message
            welcome_msg = page.locator('div[aria-label="Chat welcome message"]')
            expect(welcome_msg).to_be_visible()
            is_user_deleted = welcome_msg.get_by_text(str(users[-1])).is_visible()
            page.wait_for_timeout(2000)

            if is_user_deleted:
                assert False, 'The removed user is displayed in the welcome group message'
            else:
                assert True, 'The removed user is not displayed in the welcome group message'

            page.wait_for_timeout(6000)
        except Exception as e:
            # Re-raise the exception after handling
            raise e
        finally:
            # Stop tracing, export, and clean the trace
            context.tracing.stop()
            context.tracing.export(path=trace_path)
            trace_cleaner(trace_path)
            browser.close()
