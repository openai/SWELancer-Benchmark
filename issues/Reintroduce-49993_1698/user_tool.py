import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
import imaplib
import logging
import sys
import re
import email
import string, random
from playwright.sync_api import sync_playwright, expect
from utils.trace_cleaner import trace_cleaner  # Added import for trace cleaner

# Expensify app URL
EXPENSIFY_URL = "https://dev.new.expensify.com:8082/"

# Email login credentials
EMAIL_USERNAME = "naturesv057@gmail.com"
EMAIL_PASSWORD = "hyjk ilxi pnom oret"

# Email username postfix
EMAIL_USERNAME_POSTFIX = "49993_4"

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
    return f"{username}+{EMAIL_USERNAME_POSTFIX}@{domain}"

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

def get_otp_from_email(username, password, retries=2, delay=2):
    """
    Read the OTP email and return the OTP code.
    """
    LOGGER.info("Reading the OTP email")
    with imaplib.IMAP4_SSL(host="imap.gmail.com") as imap:
        imap.login(username, password)
        for i in range(1, retries + 1):
            imap.select("inbox")
            status, messages = imap.search(None, "ALL")
            if status == "OK":
                for message_id in reversed(messages[0].split()):
                    status, data = imap.fetch(message_id, "(RFC822)")
                    if status == "OK":
                        email_message = email.message_from_bytes(data[0][1])
                        subject, encoding = email.header.decode_header(email_message["Subject"])[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding)
                        if subject.startswith("Expensify magic sign-in code:"):
                            otp_code = subject.split(":")[-1].strip()
                            LOGGER.info("Got the OTP %s", otp_code)
                            return otp_code
            time.sleep(delay)
        imap.close()
    return "123456"

def launch_browser(pw, headless=True, device=None, geolocation=None):
    """
    Launch the browser.
    """
    browser = pw.chromium.launch(
        headless=True,
        proxy={
            'server': 'http://127.0.0.1:8080',
        },
        args=[
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
        ],
    )
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
    # Clear the email inbox
    clear_inbox(EMAIL_USERNAME, EMAIL_PASSWORD)
    # Open the Expensify app
    page.goto(EXPENSIFY_URL)
    # Login user
    page.get_by_test_id("username").fill(email)
    page.get_by_role("button", name="Continue").click()

    # Get the OTP and complete verification
    otp_code = get_otp_from_email(EMAIL_USERNAME, EMAIL_PASSWORD)
    page.get_by_test_id("validateCode").fill(otp_code)
    # Check if onboarding is required
    try:
        expect(page.get_by_text("What do you want to do today?")).to_be_visible()
    except AssertionError:
        pass
    else:
        # Complete the onboarding
        page.get_by_label("Track and budget expenses").click()
        page.get_by_role("textbox", name="First name").fill(first_name)
        page.get_by_role("textbox", name="Last name").fill(last_name)
        page.get_by_role("button", name="Continue").click()
    # Expect the main screen to appear
    expect(page.get_by_test_id("BaseSidebarScreen")).to_be_visible(timeout=1000)

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
    page.get_by_text(workspace_name).first.click()
    page.wait_for_timeout(2000)

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

def test_merchant_info_field_is_required_appeared():
    with sync_playwright() as p:
        # Launch browser
        browser, context, page = launch_browser(p)
        # Start tracing
        context.tracing.start(screenshots=True, snapshots=True, sources=True)

        trace_path = "/app/expensify/user_tool/output_browser1.zip"

        try:
            #Step 1: Login user1
            email = generate_user_email()
            LOGGER.info("User email %s", email)
            login_user(page, email)
            page.wait_for_timeout(5000)

            LOGGER.info("User logged in successfully")

            #Step 2: Create new workspace
            page = create_and_click_workspace(page)
            
            #Step 3: Create submit expense
            page.get_by_role("button", name="Create").click()
            page.wait_for_timeout(1000)
            page.get_by_text("Submit expense", exact=True).click()
            page.wait_for_timeout(1000)
            page.get_by_label("Manual").click()
            page.wait_for_timeout(1000)
            page.get_by_label("Select a currency").click()
            page.wait_for_timeout(1000)
            page.get_by_test_id("selection-list-text-input").fill("TRY")
            page.wait_for_timeout(1000)
            page.get_by_label("TRY - TL").click()
            page.wait_for_timeout(1000)
            page.get_by_placeholder("0").fill("111")
            page.wait_for_timeout(1000)
            page.locator("#numPadContainerView").get_by_role("button", name="Next").click()
            page.wait_for_timeout(1000)

            #Step 4: Enter Desc and Merchant
            page.get_by_text("Description").click()
            page.wait_for_timeout(1000)
            page.get_by_role("textbox", name="What's it for?").fill("Description")
            page.wait_for_timeout(1000)
            page.get_by_role("button", name="Save").click()
            page.wait_for_timeout(1000)
            page.locator("div").filter(has_text=re.compile(r"^Merchant$")).nth(3).click()
            page.wait_for_timeout(1000)
            page.get_by_role("textbox", name="Merchant").fill("Merchant1")
            page.wait_for_timeout(1000)
            page.get_by_role("button", name="Save").click()
            page.wait_for_timeout(1000)
            page.get_by_role("button", name="Submit TRY").click()
            page.wait_for_timeout(1000)
            page.get_by_label("View details").click()

            page.wait_for_timeout(1000)

            #Step 5: Assertion
            # Extract the created report id
            report_id = get_expnse_report_id(page)

            all_highlighted_text = page.get_by_test_id(report_id).inner_text()
            highlighted_text = all_highlighted_text.split("\n")[-1].split()[-1]

            # Check for subject line of expense
            assert highlighted_text=="Merchant1"
        except Exception as e:
            # We still want to save the trace
            raise e
        finally:
            # Stop tracing and export
            context.tracing.stop()
            context.tracing.export(trace_path)
            trace_cleaner(trace_path)
            browser.close()
