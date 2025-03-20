import logging
import time

from playwright.sync_api import sync_playwright, Page

NEW_DOT_URL = "https://dev.new.expensify.com:8082"
EMAIL = "testexpensifyturing+034@gmail.com"
PASSWORD = ""


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
        import imaplib
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
        import email
        from email.header import decode_header
        import re

        logging.info("Attempting to read OTP code from emails.")

        # Loop to retry fetching the OTP for a specified number of attempts
        for i in range(retries):

            # Search for unread emails with the subject "Expensify magic sign-in code:"
            self.imap.select("inbox")
            status, messages = self.imap.search(None, '(UNSEEN SUBJECT "Expensify magic sign-in code:")')

            # Check if the search was successful
            if not status == "OK":
                logging.error(f"Failed to search for emails. Retrying {i + 1}/{retries}...")
                time.sleep(delay)
                continue

            # If there are any matching emails, process the latest one
            email_ids = messages[0].split()
            if not email_ids:
                logging.info(f"Failed to retrieve emails. Retrying {i + 1}/{retries}...")
                time.sleep(delay)
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
            time.sleep(delay)

        logging.warning("Max retries reached. OTP code not found.")

        return None


def sign_in_new_dot(page: Page, email: str, password: str, mock_otp):
    with EmailHandler(email, password) as email_handler:
        if not mock_otp:
            email_handler.clean_inbox()  # Clean inbox

        page.get_by_test_id("username").fill(email)
        page.get_by_role("button", name="Continue").click()

        # Read and enter
        otp = email_handler.read_otp_code() if not mock_otp else "123456"
        page.get_by_test_id("validateCode").fill(otp)


uncaught_error_detected = False


def check_uncaught_errors(error):
    print("\nError detected:", error, end="")
    global uncaught_error_detected
    uncaught_error_detected = True


def test_expensify_52633():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--ignore-certificate-errors",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
            ],
            proxy={"server": "http://127.0.0.1:8080/"},
            slow_mo=500
        )
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()

        page.goto(NEW_DOT_URL)
        user_email = EMAIL
        sign_in_new_dot(page, user_email, PASSWORD, mock_otp=True)

        # Set offline and Clear Cache
        page.get_by_label("Inbox").wait_for()
        page.context.set_offline(True)
        page.get_by_role("button", name="My settings").click()
        page.get_by_test_id("InitialSettingsPage").get_by_role("menuitem", name="Troubleshoot").click()
        page.get_by_test_id("TroubleshootPage").get_by_role("menuitem", name="Clear cache and restart").click()
        page.get_by_role("button", name="Reset and refresh").click()

        page.on("pageerror", check_uncaught_errors)

        # Click Search Icon
        page.get_by_test_id("TroubleshootPage").get_by_label("Search").click()

        assert not uncaught_error_detected, "Exception occurred on pressing search key"
