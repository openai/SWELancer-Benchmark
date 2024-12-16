import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
import imaplib
import logging
import sys
import re
import email
from playwright.sync_api import sync_playwright
import random
from email.header import decode_header

from utils.trace_cleaner import trace_cleaner

# Expensify app URL
EXPENSIFY_URL = "https://dev.new.expensify.com:8082/"

# Email login credentials
EMAIL_USERNAME = "rgulraiz2000@gmail.com"
EMAIL_PASSWORD = "kepw uquj myoa npvj"


# Email username postfix
EMAIL_USERNAME_POSTFIX = "49995"

# Logger
logging.basicConfig(level=logging.INFO, stream=sys.stdout, format="%(message)s")
LOGGER = logging.getLogger(__name__)

def generate_user_email(user_id=None):
    """
    Generate an email address for a user login.
    """
    temp = EMAIL_USERNAME.rsplit("@", 1)
    username = temp[0].strip()
    domain = temp[1].strip()
    return f"{username}+{EMAIL_USERNAME_POSTFIX}{user_id or ''}@{domain}"

def clear_inbox(username, password):
    """
    Delete all existing messages from the Inbox.
    """
    LOGGER.info("Deleting all existing messages from the email inbox")
    with imaplib.IMAP4_SSL(host="imap.gmail.com") as imap:
        imap.login(username, password)
        imap.select("inbox")
        imap.store("1:*", "+FLAGS", "\\Deleted")
        imap.expunge()
        imap.close()

def get_magic_code(user_email, password, retries=5, delay=5):
    # Connect to the server
    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    imap.login(user_email, password)

    for _ in range(retries):
        imap.select("inbox")
        status, messages = imap.search(None, '(UNSEEN SUBJECT "Expensify magic sign-in code:")')

        if status == "OK":
            email_ids = messages[0].split()
            if email_ids:
                latest_email_id = email_ids[-1]
                status, msg_data = imap.fetch(latest_email_id, "(RFC822)")

                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        subject, encoding = decode_header(msg["Subject"])[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding or "utf-8")

                        # Search for the magic code in the subject
                        match = re.search(r"Expensify magic sign-in code: (\d+)", subject)
                        if match:
                            code = match.group(1)
                            imap.logout()
                            return code
            else:
                print("No unread emails found with the subject. Retrying...")
        else:
            print("Failed to retrieve emails. Retrying...")

        # Wait for the specified delay before trying again
        time.sleep(delay)

    imap.logout()
    print("Max retries reached. Email not found.")
    return None


def launch_browser(pw, headless=True, device=None, geolocation=None):
    """
    Launch the browser.
    """
    # Launch the Chromium browser (headless = False)
    # browser = pw.chromium.launch(headless=True)
    browser = pw.chromium.launch(headless=True,args=[ # Set headless=True for headless mode
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ])
    context_args = {}
    if device:
        context_args.update(pw.devices[device])
    if geolocation:
        context_args["geolocation"] = geolocation
        context_args["permissions"] = ["geolocation"]
    context = browser.new_context(**context_args)
    page = context.new_page()
    return browser, context, page


def login_user(page, email, first_name="John", last_name="Doe"):
    """
    Login to the Expensify app and complete the onboarding.
    """
    # Open the Expensify app
    page.goto(EXPENSIFY_URL)
    # Login user
    page.get_by_test_id("username").fill(email)
    page.get_by_role("button", name="Continue").click()
    page.wait_for_timeout(3000)

    if page.get_by_role("button", name="Join").is_visible():
        page.get_by_role("button", name="Join").click()
    else:
        # Get the OTP and complete verification
        # otp_code = get_magic_code(EMAIL_USERNAME, EMAIL_PASSWORD)
        otp_code = "000000"
        page.get_by_test_id("validateCode").fill(otp_code)
        # Expect the main screen to appear
    page.wait_for_timeout(10000)

def extract_workspace_name(text):
    """
        Extract the workspace name from description.
    """
    start_phrase = "You have been invited to "
    end_phrase = "! Download the Expensify"

    # Find the start index of the content to extract
    start_index = text.find(start_phrase) + len(start_phrase)

    # Find the end index of the content to extract
    end_index = text.find(end_phrase)

    # Slice the string to extract the content and return it
    return text[start_index:end_index]

def create_and_click_workspace(page):  
    """
        Create workspace, extract the workspace name from description and click on it.
    """ 
    page.get_by_label("My settings").click()
    page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()
    page.get_by_label("New workspace").first.click()

    # Get default created workspace name
    text = page.get_by_test_id("comment").locator("div").filter(
        has_text="You have been invited to").first.inner_text()
    workspace_name = extract_workspace_name(text)

    # Click on workspace
    page.get_by_label("Back").click()
    page.get_by_label("Inbox", exact=True).click()
    page.wait_for_timeout(3000)
    elements = page.get_by_text(workspace_name)
    if elements.count() > 1:
        try:
            page.get_by_text(workspace_name).last.click()
        except:
            pass

        try:
            page.get_by_text(workspace_name).nth(1).click()
        except:
            pass

    return page

def submit_expense(page):
    """
        Submit the expanse from workspace and click on created expanse.
    """ 

    # Click for submit expense
    page.locator(
        "div:nth-child(4) > div:nth-child(2) > div:nth-child(2) > div > div > div > div > div > div > div > div > div:nth-child(2) > div > div:nth-child(3) > div > div:nth-child(2) > div > div > div > div:nth-child(4) > div").click()

    # Submit expense
    page.get_by_label("Submit expense").click()
    page.get_by_label("Manual").click()
    
    # get random amount to avoid duplicates in case of multiple runs
    random_number = random.randint(100, 999)
    page.get_by_placeholder("0").fill(str(random_number))

    page.locator("#numPadContainerView").get_by_role("button", name="Next").click()
    page.get_by_role("menuitem", name="Description").click()
    page.get_by_role("textbox", name="What's it for?").fill("description")
    page.get_by_role("button", name="Save").click()
    page.get_by_role("menuitem", name="Merchant Required").click()
    page.get_by_role("textbox", name="Merchant").fill("merchant1")
    page.get_by_role("button", name="Save").click()
    page.get_by_role("button", name="Submit").click()

    # Click on expense
    if page.get_by_label("View details").count() > 1:
        page.get_by_label("View details").last.click()
    else:
        page.get_by_label("View details").click()
    return page

def get_expnse_report_id(page):
    """
        Extract the report id from expanse header
    """ 
    text = page.get_by_label("Expense Report #").first.inner_text()
    # Use regular expression to find the number following "Expense Report #"
    match = re.search(r'Expense Report #(\d+)', text)
    if match:
        report_id = match.group(1)
    return report_id

def test_expense_detail_display():
    with sync_playwright() as pw:
        email = generate_user_email()
        LOGGER.info("User email %s", email)
        browser, context, page = launch_browser(pw)
        # Start tracing
        context.tracing.start(screenshots=True, snapshots=True, sources=True)

        try:
            login_user(page, email)
            LOGGER.info("User logged in successfully")

            # Create workspace and click it
            page = create_and_click_workspace(page)

            # Submit expense from workspace
            page = submit_expense(page)

            # Extract the created report id
            report_id = get_expnse_report_id(page)

            all_highlighted_text = page.get_by_test_id(report_id).inner_text()
            highlighted_text = all_highlighted_text.split("\n")[-1].split()[-1]

            # Check for subject line of expense
            assert highlighted_text=="merchant1"
        finally:
            # Stop tracing and export
            context.tracing.stop()
            context.tracing.export(path="/app/expensify/user_tool/output_browser1.zip")
            # Clean the trace
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            # Close the browser
            page.close()
            context.close()
            browser.close()
