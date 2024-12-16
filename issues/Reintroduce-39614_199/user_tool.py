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

# Added import for trace_cleaner
from utils.trace_cleaner import trace_cleaner

# Expensify app URL
EXPENSIFY_URL = "https://dev.new.expensify.com:8082/"

# Email login credentials
EMAIL_USERNAME = "naturesv057@gmail.com"
EMAIL_PASSWORD = "hyjk ilxi pnom oret"

# Email username postfix
EMAIL_USERNAME_POSTFIX = "39614_2"

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

def get_otp_from_email(username, password, retries=1, delay=1):
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

def reproduce_scenario(page) -> None:
    # Step 1: Create workspace
    page.get_by_label("My settings").click()
    page.wait_for_timeout(1000)
    page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()
    page.wait_for_timeout(1000)
    page.get_by_label("New workspace").first.click()
    page.wait_for_timeout(1000)

    # Step 2: Open workspace setting page
    features_text_element = page.locator('div[dir="auto"]', has_text="More features")
    features_text_element.click()
    page.wait_for_timeout(1000)

    # Step 3: Enable the taxes for the workspace
    documement_button = page.get_by_label("Document and reclaim eligible")
    documement_button.click()
    page.wait_for_timeout(1000)

    taxes_button = page.get_by_test_id("WorkspaceInitialPage").get_by_label("Taxes")
    taxes_button.click()
    page.wait_for_timeout(1000)

    # Step 4: Add taxes information
    add_rate = page.get_by_role("button", name="Add rate")
    add_rate.click()
    page.wait_for_timeout(1000)

    tax_name_button = page.get_by_test_id("WorkspaceCreateTaxPage").get_by_text("Name")
    tax_name_button.click()
    page.wait_for_timeout(1000)
    page.get_by_role("textbox", name="Name").fill("1/")
    page.wait_for_timeout(1000)

    save_button = page.get_by_test_id("TextSelectorModal").get_by_role("button", name="Save")
    save_button.click()
    page.wait_for_timeout(1000)

    tax_value_button = page.get_by_text("Value")
    tax_value_button.click()
    page.wait_for_timeout(1000)
    page.get_by_placeholder("0").fill("1")
    page.wait_for_timeout(1000)
    save_button = page.get_by_test_id("AmountSelectorModal").get_by_role("button", name="Save")
    save_button.click()
    page.wait_for_timeout(1000)

    save_button = page.get_by_role("button", name="Save").last
    save_button.click()
    page.wait_for_timeout(1000)
    page.locator("button").filter(has_text="/1%").click()
    page.wait_for_timeout(1000)

    # Verify that 'Hmm... it's not here' text is not visible
    element = page.locator('div[dir="auto"]', has_text="Hmm... it's not here")
    page.wait_for_timeout(1000)
    expect(element).not_to_be_visible()

def test_not_here_text_in_settings_page() -> None:
    with sync_playwright() as p:
        email = generate_user_email()
        LOGGER.info("User email %s", email)
        browser, context, page = launch_browser(p)

        # Start tracing
        context.tracing.start(
            title="Test Not Here Text In Settings Page",
            screenshots=True,
            snapshots=True,
            sources=True
        )

        try:
            # Login user
            login_user(page, email)
            page.wait_for_timeout(5000)
            LOGGER.info("User logged in successfully")

            # Reproduce scenario
            reproduce_scenario(page)

            time.sleep(1)
        except Exception as e:
            # Re-raise the exception after handling
            raise e
        finally:
            # Stop tracing and save
            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            context.tracing.stop(path=trace_path)

            # Clean the trace
            trace_cleaner(trace_path)

            # Close context and browser
            context.close()
            browser.close()
