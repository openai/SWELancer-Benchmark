import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

"""
This is a test that logs in three users to verify the flow of two approvers and make sure the second approver can't see the submit button in a delayed submission.
"""

import re
import time
import logging
import pytest
from playwright.async_api import Page, expect
from playwright.async_api import async_playwright
import os
import imaplib
import email
from email.header import decode_header

# Email
BASE_EMAIL = "testerfreelancer555@gmail.com"
PASSWORD = "snct ajbr yadx kwlq"
ISSUE_NUMBER = "48778_1"
SUBMITTER_SUFFIX = f"{ISSUE_NUMBER}112"
APPROVER_1_SUFFIX = f"{ISSUE_NUMBER}111"
APPROVER_2_SUFFIX = f"{ISSUE_NUMBER}113"


NEW_DOT_URL = "https://dev.new.expensify.com:8082"
OLD_DOT_URL = "http://localhost:9000/"


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

# Sign in to Expensify
async def sign_in(page: Page, email: str, password: str, expensify_dot: str="NewDot", url_new_dot: str=None, url_old_dot: str=None, mock_otp: bool=False):
    """
    Sign in into the Expensify dot.
    """

    url_new_dot = url_new_dot if url_new_dot else NEW_DOT_URL
    url_old_dot = url_old_dot if url_old_dot else OLD_DOT_URL

    if expensify_dot == "NewDot":
        if await check_if_logged_in(page=page, url=url_new_dot):
            return
        await sign_in_new_dot(page=page, email=email, password=password, mock_otp=mock_otp)
    elif expensify_dot == "OldDot":
        if await check_if_logged_in(page=page, url=url_old_dot):
            return
        await sign_in_old_dot(page=page, email=email, password=password, mock_otp=mock_otp)
    else:
        raise ValueError("Invalid Expensify dot provided. Please provide either 'NewDot' or 'OldDot'.")


async def check_if_logged_in(page: Page, url: str):
    """
    Check if the user is already logged in by navigating to the specified URL.
    Args:
        page (Page): The Playwright page object.
        url (str): The URL to navigate to before checking login status.
    Returns:
        bool: True if logged in, False otherwise.
    """
    await page.goto(url)
    try:
        await expect(page.get_by_label("Inbox")).to_be_visible()
        logging.info("User is already logged in.")
        return True
    except:
        logging.info("User is not logged in.")
        return False


# Sign In to Expensify
async def sign_in_new_dot(page: Page, email: str, password: str, mock_otp: bool=False):
    """
    Sign in into the new Expensify dot.
    """
    
    # Sign In
    with EmailHandler(email, password) as email_handler:
        # Clean inbox
        if not mock_otp:
            email_handler.clean_inbox()

        # Enter email
        await page.get_by_test_id("username").fill(email)
        await page.get_by_role("button", name="Continue").click()
  
        await page.wait_for_timeout(2000)
        # Await OTP
        otp = "123456" if mock_otp else email_handler.read_otp_code()
        await page.get_by_test_id("validateCode").fill(otp)

        # Wait sign in to complete
        await page.get_by_text("Please enter the magic code").wait_for(state="hidden")
        logging.info("Sign in complete.")

async def sign_in_old_dot(page: Page, email: str, password: str, mock_otp: bool=False):
    """
    Signs in into the old Expensify dot.
    Note this will redirect to the PRODUCTION URL, be careful
    """

    # Sign In
    with EmailHandler(email, password) as email_handler:
        # Clean inbox
        if not mock_otp:
            email_handler.clean_inbox()

        # Enter email
        await page.get_by_role("button", name="Sign In").click()
        await page.get_by_role("button", name="Email ").click()
        await page.get_by_placeholder("Enter your email to begin").fill(email)
        await page.get_by_role("button", name="Next").click()

        # Await OTP
        otp = "123456" if mock_otp else email_handler.read_otp_code()
        await page.get_by_placeholder("Magic Code").fill(otp)
        await page.locator("#js_click_signIn").click()
  
        # Wait sign in to complete
        await page.wait_for_selector('input[placeholder="Magic Code"]', state="hidden")
        logging.info("Sign in complete.")
 
# Set up browser
async def start_browser(headless=True, persistent=False, data_dir=None, launch_args=None, slow_mo=None):
    """
    Start a browser instance with the given parameters.

    :param headless: Boolean to specify if the browser should run in headless mode.
    :param persistent: Boolean to specify if the browser context should be persistent.
    :param data_dir: Directory to store browser data for persistent context.
    :param launch_args: List of arguments to pass to the browser instance.
    :param slow_mo: Slow down the browser operations by the specified amount of milliseconds.
    :return: A tuple of (context, page, playwright).
    """
    if launch_args is None:
        launch_args = ["--ignore-certificate-errors"]

    # Initialize Playwright
    playwright = await async_playwright().start()
    context, page = None, None
    if persistent:
        if data_dir is None:
            data_dir = 'browser_context'
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

        context = await playwright.chromium.launch_persistent_context(
            data_dir,
            headless=headless,
            args=launch_args,
            slow_mo=slow_mo
        )
        page = context.pages[0]
    else:
        browser = await playwright.chromium.launch(
            channel="chrome",
            headless=True,
            args=[
                "--ignore-certificate-errors",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process"
            ],
            proxy={"server": "http://localhost:8080"},
            slow_mo=1000
        )
        context = await browser.new_context(ignore_https_errors=True)
        page = await context.new_page()
    
    logging.info("The browser has been started.")

    return context, page, playwright  # Return playwright to close later


# Function to reset browser
async def close_browser(context, page, playwright):
    await page.close()
    await context.close()
    await playwright.stop()  # Explicitly stop Playwright
    logging.info("The browser has been stopped.")

def get_specific_derived_email(email: str, suffix: str):
    """
    Derive the email from the user email.
    Will append the suffix to the email: `user_name+suffix@domain`
    """
    user_name, domain = email.split('@')
    return f"{user_name}+{suffix}@{domain}"


async def new_browser(playwright):
    browser = await playwright.chromium.launch(
        channel="chrome",
        headless=True,
        args=[
            "--ignore-certificate-errors",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ],
        proxy={"server": "http://localhost:8080"},
        slow_mo=1000
    )
    return browser

async def login_two_users(playwright):
    browser = await new_browser(playwright)
        
    page_submitter = await browser.new_page()
    email_submitter = get_specific_derived_email(email=BASE_EMAIL, suffix=SUBMITTER_SUFFIX)
    await sign_in(page_submitter, email=email_submitter, password=PASSWORD,mock_otp=True)
    
    page_approver_2 = await browser.new_page()
    email_approver_2 = get_specific_derived_email(email=BASE_EMAIL, suffix=APPROVER_2_SUFFIX)
    await sign_in(page_approver_2, email=email_approver_2, password=PASSWORD,mock_otp=True)

    return browser, page_submitter, page_approver_2

async def create_a_new_workspace(page):
    # Going to the settings page
    await page.get_by_label("My settings").click()
    # Accessing the workspace's page
    await page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").get_by_text("Workspaces").click()
    # Creating a new workspace
    await page.wait_for_timeout(3000) # Waiting the page to load because the loading page has two buttons which might cause an exception because none of them work
    try:
        await page.get_by_label("New workspace").click()
    except:
        await page.get_by_label("New workspace").first.click() # In case there is no workspace yet

    await page.get_by_test_id("WorkspacePageWithSections").get_by_text("Name").click()
    random_name = "Workspace453"
    await page.get_by_role("textbox", name="Name").fill(random_name)
    await page.get_by_role("button", name="Save").click()

    return random_name

async def submit_expense(page):
    await page.get_by_label("Create").last.click()
    await page.get_by_text("Submit expense", exact=True).click()
    await page.get_by_label("Manual").click()
    await page.get_by_placeholder("0").fill("1")
    await page.locator("#numPadContainerView").get_by_role("button", name="Next").click()
    try:
        await page.get_by_text("Merchant").click()
    except:
        await page.get_by_text("Merchant").last.click()

    await page.get_by_role("textbox", name="Merchant").fill("test")
    await page.get_by_role("button", name="Save").click()
    await page.get_by_role("button", name="Submit").click()

async def access_target_workspace_chat(page, chat_name, submitter=False):
    await page.reload()
    await page.get_by_label("Workspaces").click()
    try:
        await page.get_by_test_id("selection-list").get_by_label(chat_name).click()
    except:
        await page.get_by_test_id("selection-list-text-input").fill(chat_name)
        await page.get_by_test_id("selection-list").get_by_label(chat_name).click()

    if not submitter:
        await page.get_by_label('Last chat message preview').filter(has_text=rf"{chat_name}").first.click()
    else:
        await page.get_by_test_id("DisplayNamesWithTooltip").filter(has_text=r"submitter").last.click()

async def adding_members_to_workspace(page):
    await page.get_by_text("Members").click()
    await page.get_by_role("button", name="Invite member").click()
    user, domain = BASE_EMAIL.split('@')
    await page.get_by_test_id("selection-list-text-input").fill(f"{user}+{SUBMITTER_SUFFIX}@{domain}")
    await page.get_by_label("submitter").last.click()

    await page.get_by_test_id("selection-list-text-input").fill(f"{user}+{APPROVER_1_SUFFIX}@{domain}")
    await page.get_by_label("approver1 user").last.click()
    await page.get_by_test_id("selection-list-text-input").fill(f"{user}+{APPROVER_2_SUFFIX}@{domain}")
    await page.get_by_label("approver2 user").last.click()
    await page.get_by_role("button", name="Next").click()
    await page.get_by_test_id("WorkspaceInviteMessagePage").get_by_role("button", name="Invite").click()

async def adding_workflow(page):
    await page.get_by_test_id("WorkspaceInitialPage").get_by_text("Workflows").click()
    await page.get_by_label("Delay expense submissions").click()   
    try:
        await page.get_by_label("Weekly").get_by_role("img").click()
    except Exception:
        # If "Weekly" is not found, click on "Manually"
        await page.get_by_label("Manually").get_by_role("img").click()
    await page.get_by_test_id("WorkspaceAutoReportingFrequencyPage").get_by_label("Manually").click()
    await page.get_by_label("Require additional approval").click()
    await page.get_by_label("Add approvals").click()
    
    await page.get_by_text("Additional approver").click()
    await page.get_by_role("button", name="Upgrade").click()
    await page.get_by_role("button", name="Got it, thanks").click()
    await page.get_by_test_id("WorkspaceWorkflowsApprovalsEditPage").get_by_text("Admin user").first.click()
    await page.get_by_test_id("WorkspaceWorkflowsApprovalsApproverPage").get_by_label("approver1").click()
    await page.get_by_role("button", name="Save").click()
    await page.get_by_text("Additional approver").click()
    await page.get_by_test_id("WorkspaceWorkflowsApprovalsApproverPage").get_by_label("approver2").click()
    await page.get_by_role("button", name="Save").click()
    await page.get_by_role("button", name="Save").click()

@pytest.mark.asyncio
async def test_submit_button():
    context, page_admin, playwright = await start_browser()
    try:
        email_admin = get_specific_derived_email(email=BASE_EMAIL, suffix=ISSUE_NUMBER)
        await sign_in(page_admin, email=email_admin, password=PASSWORD,mock_otp=True)

        browser, page_submitter, page_approver_2 = await login_two_users(playwright)

        # Creating a new workspace
        workspace_name = await create_a_new_workspace(page_admin)
        # Adding members to workspace
        await adding_members_to_workspace(page_admin)
        # Enabling workflow
        await page_admin.get_by_text("More features").click()
        await page_admin.get_by_label("Configure how spend is").click()
        # Adding a new workflow
        await adding_workflow(page_admin)

        # Deleting the default workflow
        try:
            await page_admin.reload()
            await page_admin.locator("button").filter(has_text="Expenses fromapprover_1,").last.click()
            await page_admin.get_by_text("Delete").click()
            await page_admin.get_by_role("button", name="Delete").click()
        except:
            pass
        
        # submitting an expense by the submitter account
        await access_target_workspace_chat(page_submitter, workspace_name)
        await submit_expense(page_submitter)

        # Checking the submit button on the approver_2 account
        await access_target_workspace_chat(page_approver_2, workspace_name, True)
        await expect(page_approver_2.get_by_role("button", name="Submit", exact=True)).not_to_be_visible()

        await page_submitter.close()
        await page_approver_2.close()
        await browser.close()

    finally:
        await close_browser(context, page_admin, playwright)

