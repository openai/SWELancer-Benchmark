import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
import re
import imaplib
import email
import logging
from email.header import decode_header
import pytest
from playwright.async_api import Page, expect, async_playwright

# Added import for trace_cleaner
from utils.trace_cleaner import trace_cleaner

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
EMAIL = "Adebayovicktor0+test49277@gmail.com"
PASSWORD = "bruzwjfovckiesys"
NEW_DOT_URL = "https://dev.new.expensify.com:8082"
OLD_DOT_URL = "http://localhost:9000/"


def get_unique_derived_email(email: str):
    """
    Derive the email from the user email.
    """
    user_name, domain = email.split('@')
    return f"{user_name}+{int(time.time())}@{domain}"

def get_specific_derived_email(email: str, suffix: str):
    """
    Derive the email from the user email.
    Will append the suffix to the email: `user_name+suffix@domain`
    """
    user_name, domain = email.split('@')
    return f"{user_name}+{suffix}@{domain}"

class EmailHandler:
    """
    A class to handle email operations such as cleaning the inbox,
    marking all unread emails as read, and reading OTP codes.
    """

    def __init__(self, user_email, password, imap_server='imap.gmail.com'):
        """
        Initializes the EmailHandler with user credentials and connects to the IMAP server.

        Args:
            user_email (str): The email address of the user.
            password (str): The password for the email account.
            imap_server (str): The IMAP server address. Defaults to 'imap.gmail.com'.
        """
        self.user_email = user_email
        self.password = password
        self.imap_server = imap_server
        self.imap = None

    def __enter__(self):
        """
        Enters the runtime context and logs into the IMAP server.
        """
        self.imap = imaplib.IMAP4_SSL(self.imap_server)
        try:
            self.imap.login(self.user_email, self.password)
            logging.info("Logged into IMAP server.")
        except Exception as e:
            logging.error(f"Failed to login to IMAP server: {e}")
            raise
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Exits the runtime context and logs out from the IMAP server.
        """
        if self.imap:
            self.imap.logout()
            logging.info("Logged out from IMAP server.")

    def clean_inbox(self):
        """
        Deletes all emails in the inbox.

        WARNING: This action is irreversible.
        """
        logging.warning("Deleting all emails in the inbox.")
        # Select the inbox folder
        status, _ = self.imap.select("INBOX")
        if status != "OK":
            logging.error("Failed to select INBOX.")
            return

        # Search for all emails
        status, messages = self.imap.search(None, 'ALL')
        if status != "OK":
            logging.error("Failed to retrieve emails.")
            return

        email_ids = messages[0].split()
        if not email_ids:
            logging.info("No emails to delete.")
            return

        # Mark all emails for deletion
        for email_id in email_ids:
            self.imap.store(email_id, '+FLAGS', '\\Deleted')

        # Permanently delete emails marked for deletion
        self.imap.expunge()
        logging.info("All emails deleted from the inbox.")

    def mark_all_unread_as_read(self):
        """
        Marks all unread emails in the inbox as read.
        """
        logging.info("Marking all unread emails as read.")
        # Select the inbox folder
        status, _ = self.imap.select("INBOX")
        if status != "OK":
            logging.error("Failed to select INBOX.")
            return

        # Search for unread emails
        status, messages = self.imap.search(None, '(UNSEEN)')
        if status != "OK":
            logging.error("Failed to retrieve unread emails.")
            return

        email_ids = messages[0].split()
        if not email_ids:
            logging.info("No unread emails to mark as read.")
            return

        # Mark each email as read
        for email_id in email_ids:
            self.imap.store(email_id, '+FLAGS', '\\Seen')
        logging.info("All unread emails marked as read.")

    def read_otp_code(self, retries=5, delay=6):
        """
        Retrieves the OTP code from unread emails.

        Args:
            retries (int): Number of retries to attempt fetching the OTP code.
            delay (int): Delay in seconds between retries.

        Returns:
            str: The OTP code if found, else None.
        """
        logging.info("Attempting to read OTP code from emails.")
        
        # Loop to retry fetching the OTP for a specified number of attempts
        for i in range(retries):

            # Search for unread emails with the subject "Expensify magic sign-in code:"
            self.imap.select("inbox")
            status, messages = self.imap.search(None, '(UNSEEN SUBJECT "Expensify magic sign-in code:")')

            # Check if the search was successful
            if not status == "OK":
                logging.error(f"Failed to search for emails. Retrying {i + 1}/{retries}...")
                continue
            
            # If there are any matching emails, process the latest one
            email_ids = messages[0].split()
            if not email_ids:
                logging.info(f"Failed to retrieve emails. Retrying {i + 1}/{retries}...")
                continue
            
            latest_email_id = email_ids[-1]
            status, msg_data = self.imap.fetch(latest_email_id, "(RFC822)")

            # Iterate over the message data to retrieve the email content
            for response_part in msg_data:
                if isinstance(response_part, tuple):

                    # Parse the email content
                    msg = email.message_from_bytes(response_part[1])
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding or "utf-8")

                    # Extract the OTP code from the email subject
                    match = re.search(r"Expensify magic sign-in code: (\d+)", subject)
                    if match:
                        code = match.group(1)
                        return code

            logging.info(f"No matching emails found. Retrying {i + 1}/{retries}...")
                
        logging.warning("Max retries reached. OTP code not found.")
        return None


# Sign In to Expensify
async def sign_in_new_dot(page: Page, email: str, password: str, url: str=None):
    """
    Sign in into the new Expensify dot.
    """
    # Go to URL
    url = url if url else NEW_DOT_URL
    await page.goto(url)
    
    # Sign In
    with EmailHandler(email, password) as email_handler:
        # email_handler.clean_inbox()  # Clean inbox

        # Enter email
        await page.get_by_test_id("username").fill(email)
        await page.wait_for_timeout(1000)
        await page.get_by_role("button", name="Continue").click()
        await page.wait_for_timeout(2000)
        # OTP is hardcoded for replay
        # otp = email_handler.read_otp_code()
        # await page.wait_for_timeout(2000)
        otp = "123456"
        await page.get_by_test_id("validateCode").fill(otp)
        await page.wait_for_timeout(2000)

        # Wait sign in to complete
        await page.get_by_text("Please enter the magic code").wait_for(state="hidden")
        await page.wait_for_timeout(3000)
        logging.info("Sign in complete.")


@pytest.mark.asyncio  # ensure you have pytest-asyncio installed
async def test_category_approvers():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel='chrome', headless=True, args=[
            "--ignore-certificate-errors",
            "--disable-web-security", 
            "--disable-features=IsolateOrigins,site-per-process"
        ])
        context = await browser.new_context()
        # Start tracing
        await context.tracing.start(screenshots=True, snapshots=True, sources=True)
        page: Page = await context.new_page()

        try:
            firstname, lastname = "Test", "49277"
            await sign_in_new_dot(page, EMAIL, PASSWORD)

            # create workspace
            await page.get_by_label("My settings").click()
            await page.wait_for_timeout(2000)
            await page.get_by_test_id("InitialSettingsPage").get_by_label(
                "Workspaces"
            ).click()
            await page.wait_for_timeout(2000)
            await page.get_by_label("New workspace").first.click()

            # Enable workflows
            await page.wait_for_timeout(2000)
            await page.get_by_label("More features").click()
            await page.wait_for_timeout(2000)
            await page.get_by_label("Configure how spend is").click()
            await page.wait_for_timeout(2000)
            await page.get_by_label("Configure when receipts are").click()
            await page.wait_for_timeout(2000)
            await page.get_by_role("button", name="Upgrade").click()
            await page.wait_for_timeout(2000)
            await page.get_by_role("button", name="Got it, thanks").click()
            await page.wait_for_timeout(2000)
            # Enable approvals
            await page.get_by_label("Workflows").click()
            await page.wait_for_timeout(2000)
            await page.get_by_label("Require additional approval").click()
            await page.wait_for_timeout(2000)
            await page.get_by_label("Add approvals").click()
            await page.wait_for_timeout(2000)
            await expect(
                page.get_by_test_id("WorkspaceWorkflowsApprovalsEditPage").get_by_text(
                    f"{firstname} {lastname}"
                )
            ).to_be_visible()
            await page.wait_for_timeout(2000)
            await page.locator("#overLayBottomButton").click()
            await page.wait_for_timeout(2000)
            # Check category approver
            await page.get_by_label("Categories").click()
            await page.wait_for_timeout(2000)
            await page.locator("#Advertising").click()
            await page.wait_for_timeout(2000)

            await page.get_by_role("menuitem", name="Approver").click()
            await page.wait_for_timeout(2000)
            await page.get_by_test_id("CategoryApproverPage").get_by_label(
                f"{firstname} {lastname}"
            ).click()
            await page.wait_for_timeout(2000)
            await expect(
                page.get_by_test_id("CategorySettingsPage").get_by_text(
                    f"{firstname} {lastname}"
                )
            ).to_be_visible()
            await page.wait_for_timeout(3000)
        finally:
            # Stop tracing and call the trace cleaner even if test fails
            await context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")

        # ---------------------
        await context.close()
        await browser.close()
