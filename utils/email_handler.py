import time
import re
import imaplib
import email
import logging
from email.header import decode_header

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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