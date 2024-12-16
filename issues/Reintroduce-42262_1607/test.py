import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
import re
import imaplib
import email
import logging
from email.header import decode_header
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page





# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
EMAIL = "Adebayovicktor0+test42262@gmail.com"
PASSWORD = "bruzwjfovckiesys"
NEW_DOT_URL = "https://dev.new.expensify.com:8082"
OLD_DOT_URL = "http://localhost:9000/"
ONE_SECOND = 1000
TWO_SECONDS = 2000


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

    def read_otp_code(self, page: Page, retries=5, delay=6):
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
def sign_in_new_dot(page: Page, email: str, password: str, url: str=None):
    """
    Sign in into the new Expensify dot.
    """
    # Go to URL
    url = url if url else NEW_DOT_URL
    page.goto(url)
    
    # Sign In
    with EmailHandler(email, password) as email_handler:

        # Enter email
        page.get_by_test_id("username").fill(email)
        page.wait_for_timeout(1000)
        page.get_by_role("button", name="Continue").click()
        # OTP is hardcoded for replay
        page.wait_for_timeout(2000)
        otp = "123456"
        page.get_by_test_id("validateCode").fill(otp)
        page.wait_for_timeout(2000)

        # Wait sign in to complete
        page.get_by_text("Please enter the magic code").wait_for(state="hidden")
        page.wait_for_timeout(3000)
        logging.info("Sign in complete.")



def test_save_description_in_submitted_expense():
    with sync_playwright() as p:
        # Step 1: Login user 
        browser = p.chromium.launch(channel='chrome', headless=True,
            proxy = {"server": "http://127.0.0.1:8080/"},
            args=[
            "--ignore-certificate-errors",
            "--disable-web-security", 
            "--disable-features=IsolateOrigins,site-per-process"
        ])
        context =browser.new_context()
        page: Page = context.new_page()

        sign_in_new_dot(page, EMAIL, PASSWORD)

        invitee_email_id = 'adebayovicktor0+tests42262@gmail.com'
        inbox_menu = page.locator('button[aria-label="Inbox"]')
        expect(inbox_menu).to_be_visible()
        inbox_menu.click()
        page.wait_for_timeout(TWO_SECONDS)

        try:
            chat_button = page.locator(f'button[aria-label="Navigates to a chat"] >> div:text-is("Chat Report")')
            chat_button.click(timeout=TWO_SECONDS)
            page.wait_for_timeout(TWO_SECONDS)
        except Exception:
            try:
                chat_button = page.locator(f'button[aria-label="Navigates to a chat"] >> div:text-is("{invitee_email_id}")')
                chat_button.click(TWO_SECONDS)
                page.wait_for_timeout(TWO_SECONDS)
            except Exception:
                pass
        page.wait_for_timeout(TWO_SECONDS)
        back_arrow_button = page.locator(f'button[aria-label="{invitee_email_id}"]').last
        expect(back_arrow_button).to_be_visible()
        back_arrow_button.click()
        page.wait_for_timeout(TWO_SECONDS)

        group_members_count_div = page.locator('div:text-is("2")')
        expect(group_members_count_div).to_be_visible()
        group_members_count_div.click()
        page.wait_for_timeout(TWO_SECONDS)

        browser.close()