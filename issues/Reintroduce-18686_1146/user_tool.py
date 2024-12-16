import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
import re
import logging
import sys
import string, random
from datetime import datetime, timezone
import imaplib
import email
from email.header import decode_header
from playwright.sync_api import sync_playwright, expect
from utils.trace_cleaner import trace_cleaner

# Expensify app URL
EXPENSIFY_URL = "https://dev.new.expensify.com:8082/"

# Email login credentials
EMAIL_USERNAME = "testsbernard3@gmail.com"
EMAIL_PASSWORD = "lglr wkwn dvcu uyqe"

# Email username postfix
EMAIL_USERNAME_POSTFIX = "18686_7"

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


def closed_successfully_message(page, email):
    page.wait_for_timeout(3000)
    page.get_by_label("My settings").click()
    page.wait_for_timeout(1000)
    page.locator("div:nth-child(6) > div > div > div > div > div > div > div > div:nth-child(2) > .css-view-175oi2r").first.click()
    page.locator("div:nth-child(2) > div:nth-child(3) > div:nth-child(2) > div > div > div > div > div > div > div > div > div > div:nth-child(2) > .css-view-175oi2r").click()
    page.wait_for_timeout(1000)
    page.get_by_role("textbox", name="Enter message here").fill("Test")
    page.wait_for_timeout(1000)
    page.locator("body").press("ControlOrMeta+c")
    page.get_by_role("textbox", name="Enter your default contact").fill(email)
    page.wait_for_timeout(1000)
    page.get_by_role("button", name="Close account").click()
    page.wait_for_timeout(1000)
    page.get_by_role("button", name="Yes, continue").click()
    page.wait_for_timeout(2000)
    # Assert if "Account closed successfully" message is visible
    assert page.get_by_text("Account closed successfully").is_visible(), "Account closure confirmation message not found."


def test_AccountClosure() -> None:
    with sync_playwright() as playwright:
        trace_path = "/app/expensify/user_tool/output_browser1.zip"
        browser, context, page = None, None, None
        try:
            # Step 1: Launch the first browser and login
            browser, context, page = launch_browser(playwright)
            context.tracing.start(screenshots=True, snapshots=True, sources=True)

            email = generate_user_email()
            LOGGER.info("User email %s", email)
            login_user(page, email)
            page.wait_for_timeout(5000)

            closed_successfully_message(page, email)
        except Exception as e:
            LOGGER.error("Test encountered an error: %s", e)
            raise
        finally:
            if context:
                try:
                    context.tracing.stop()
                    context.tracing.export(trace_path)
                    trace_cleaner(trace_path)
                except Exception as ex:
                    LOGGER.error("Error during trace save/cleanup: %s", ex)

            if page:
                page.close()
            if context:
                context.close()
            if browser:
                browser.close()
            playwright.stop()
