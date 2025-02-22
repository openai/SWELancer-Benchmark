import time
import imaplib
import email
import re
import logging
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page
from enum import Enum
from email.header import decode_header


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

TEST_URL = "https://dev.new.expensify.com:8082/" 

USER_NAME = "bobexpensifytest" 
USER_PASSWORD = "aymv mpce nrvd cvye " 
FIRST_NAME = "Bob"
LAST_NAME = "Test"

#### UTILS
class TodayOptions(Enum):
    TRACK_AND_BUDGET_EXPENSES = 1
    SOMETHING_ELSE = 4

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
 
# NOTE: This function depends on the `USER_NAME` and `USER_PASSWORD` global variables defined in the CONFIG section.
def get_test_user_info(seed = None):
    """
    Get test user info using the seed:
    - If `seed` is None, this function will return a fixed email and name.
    - If `seed` is the `True` boolean value, this function will generate a random number based on the current timestamp and use it as the seed to return a random email and name.
    - Otherwise, this function will return a derivative of the fixed email and corresponding name.
    """
    if seed is None:
        return {"email": f"{USER_NAME}@gmail.com", "password": USER_PASSWORD, "first_name": f"{FIRST_NAME}", "last_name": f"{LAST_NAME}"}
    
    if type(seed) == type(True):
        seed = int(time.time())

    return {"email": f"{USER_NAME}+{seed}@gmail.com", "password": USER_PASSWORD, "first_name": f"{FIRST_NAME}", "last_name": f"{LAST_NAME}"}

def wait(page, for_seconds=1):
    page.wait_for_timeout(for_seconds * 1000)
   
def choose_what_to_do_today_if_any(page, option: TodayOptions, retries = 5, **kwargs):
    wait(page, 5)

    for _ in range(retries):
        wdyw = page.locator("text=What do you want to do today?")
        if wdyw.count() == 0:
            page.reload()
        else:
            break

    if wdyw.count() == 0:
        return     
        
    if option == TodayOptions.SOMETHING_ELSE:
        text = "Something else"
    elif option == TodayOptions.TRACK_AND_BUDGET_EXPENSES:
        text='Track and budget expenses'

    page.locator(f"text='{text}'").click()
    page.get_by_role("button", name="Continue").click()

    # Enter first name, last name and click continue
    wait(page)
    page.locator('input[name="fname"]').fill(kwargs['first_name'])
    page.locator('input[name="lname"]').fill(kwargs['last_name'])
    page.get_by_role("button", name="Continue").last.click()

def close_navigation_popup_if_present(page, timeout=4000):
    try:
        page.locator('button[aria-label="Close"]').wait_for(timeout=timeout)
        page.locator('button[aria-label="Close"]').click()
    except:
        return

def choose_link_if_any(page, link_text, retries = 5):
    wait(page)

    for _ in range(retries):
        link = page.locator(f'text={link_text}')
        if link.count() == 0:
            print(f'"{link_text}" link is not found. Wait and retry...')
            wait(page)
        else:
            break

    if link.count() == 0:
        print(f'"{link_text}" link is not found.')
        return 
    
    expect(link).to_be_visible()
    link.click()

def login(p: PlaywrightContextManager, user_info, if_phone=False) -> tuple[Browser, Page, str]:    
    # Step 1: Input email and click Continue
    permissions = ['clipboard-read', 'clipboard-write']
    browser = p.chromium.launch(
        channel="chrome",
        headless=False,
        args=[
            "--ignore-certificate-errors",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ],
        proxy={"server": "http://localhost:8080"},
        slow_mo=1000
    )
    email=user_info["email"]
    password=user_info["password"]

    if if_phone:
        phone = p.devices['iPhone 12 Pro']
        context = browser.new_context(**phone, permissions=permissions, reduced_motion='no-preference')
    else:
        context = browser.new_context()

    page = context.new_page()

    page.goto(TEST_URL, timeout=60000) # Timeout is set to 60 seconds to avoid a Timeout error in my environment - native MacOS M1 Max. Perhaps you can set it to a lower value if you have a faster environment.

    with EmailHandler(email, password) as email_handler:
        email_handler.clean_inbox()  # Clean inbox

        phone_or_email_input = page.locator('input[type="email"]')
        phone_or_email_input.fill(email)

        continue_button = page.locator('button:has-text("Continue")')
        continue_button.click()

        # Step 2: Click Join button if the user is new. Or, use Magic Code to sign in if the user is existing.
        wait(page)

        join_button = page.locator('button:has-text("Join")')
        if join_button.count() > 0:
            join_button.click()
        else:
            otp = email_handler.read_otp_code()
            page.get_by_test_id("validateCode").fill(otp)

    return browser, page

#### TESTS

def test():
    with sync_playwright() as p:
        # Step 1: Login
        user_info1 = get_test_user_info(seed=1739663792)
        browser1, page1 = login(p, user_info1, False)

        choose_what_to_do_today_if_any(page1, TodayOptions.TRACK_AND_BUDGET_EXPENSES, **user_info1)

        user_info2 = get_test_user_info(seed=1739663816) 
        browser, page2 = login(p, user_info2, False)

        choose_what_to_do_today_if_any(page2, TodayOptions.TRACK_AND_BUDGET_EXPENSES, **user_info2)

        close_navigation_popup_if_present(page2)
        page2.locator('button[aria-label="Start chat (Floating action)"]').click()

        page2.locator('div[aria-label="Start chat"]').click()

        phone_or_email_input = page2.locator('input[aria-label="Name, email, or phone number"]')
        phone_or_email_input.fill(user_info1["email"])

        page2.wait_for_timeout(1000)

        page2.locator('button[role="button"]', has_text=user_info1["email"]).click()

        message_input = page2.locator('div[class="react-native-live-markdown-input-multiline"]').last
        message_input.fill("Hiiii")
        message_input.press("Enter")

        page1.reload()

        close_navigation_popup_if_present(page1)
        page1.locator('div[aria-label="Last chat message preview"]', has_text="Hiiii").click()

        page1.locator('span', has_text="Hiiii").last.click(button="right")

        page1.locator('div[aria-label="Join thread"]').click()

        page1.locator('button[aria-label="My settings"]').click()

        close_navigation_popup_if_present(page1)        
        page1.locator('button[aria-label="Inbox"]').click()

        welcome_message = page1.locator('div[aria-label="Chat welcome message"]').last

        expect(welcome_message).to_be_visible()
