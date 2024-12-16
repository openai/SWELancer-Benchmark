import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import email
import imaplib
import logging
import platform
import sys
import pytest
from playwright.sync_api import sync_playwright, expect
import time

# Expensify app URL
EXPENSIFY_URL = "https://dev.new.expensify.com:8082/"

# Email login credentials
EMAIL_USERNAME = "expensifytesting1@gmail.com"
EMAIL_PASSWORD = "redx tbmr hzpc rbzr"

# Logger
logging.basicConfig(level=logging.INFO, stream=sys.stdout, format="%(message)s")
LOGGER = logging.getLogger(__name__)


def clear_inbox(username, password):
    """
    Delete all the messages from the Inbox.
    """
    LOGGER.info("Deleting all the messages from the email inbox")
    with imaplib.IMAP4_SSL(host="imap.gmail.com") as imap:
        imap.login(username, password)
        imap.select("inbox")
        imap.store("1:*", "+FLAGS", "\\Deleted")
        imap.expunge()
        imap.close()


def get_otp_from_email(username, password, retries=12, delay=5):
    """
    Read the OTP email and return the OTP code.
    """
    try:
        LOGGER.info("Checking the OTP email")
        with imaplib.IMAP4_SSL(host="imap.gmail.com") as imap:
            imap.login(username, password)
            for _ in range(1, retries + 1):
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
        raise AssertionError("Failed to read the OTP from the email")
    except (AssertionError, TimeoutError):
        otp_code = '123456'
        return otp_code

def launch_browser(pw, headless=True, device=None, geolocation=None):
    """
    Launch the browser.
    """
    browser = pw.chromium.launch(headless=headless, args=[
                "--ignore-certificate-errors",
                "--disable-web-security",
                "--disable-features-IsolateOrigins,site-per-process"
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


def login_user(page, email= EMAIL_USERNAME, first_name="John", last_name="Doe"):
    """
    Log into the Expensify app.
    """
    # Clear the email inbox
    clear_inbox(EMAIL_USERNAME, EMAIL_PASSWORD)
    # Open the Expensify app
    page.goto(EXPENSIFY_URL)
    # Login user
    page.get_by_test_id("username").fill(email)
    page.get_by_role("button", name="Continue").click()
    # Check if OTP is required for the login
    try:
        expect(page.get_by_test_id("SignInPage").get_by_test_id("validateCode")).to_be_visible(timeout=7000)
    except (AssertionError, TimeoutError):
        # If not required, expect the join button to appear and click the button
        page.get_by_test_id("SignInPage").get_by_role("button", name="Join").click()
    else:
        # Get the OTP and complete verification
        otp_code = get_otp_from_email(EMAIL_USERNAME, EMAIL_PASSWORD)
        page.get_by_test_id("SignInPage").get_by_test_id("validateCode").fill(otp_code)
    
    if page.get_by_text("Track and budget expenses").is_visible():
        # Complete the onboarding
        page.get_by_label("Track and budget expenses").click()
        page.get_by_role("textbox", name="First name").fill(first_name)
        page.get_by_role("textbox", name="Last name").fill(last_name)
        page.get_by_role("button", name="Continue").click()
        # Exit the Concierge chat, if opened by default
        try:
            page.get_by_role("button", name="Back").first.click(timeout=3000)
        except (AssertionError, TimeoutError):
            pass
    # Dismiss the "Get started here!" tool tip, if shown
    try:
        page.get_by_role("button", name="Close").click(timeout=3000)
    except (AssertionError, TimeoutError):
        pass
    # Expect the main screen to appear
    expect(page.get_by_test_id("BaseSidebarScreen")).to_be_visible(timeout=10000)

def test_troubleshoot_modal():
    with sync_playwright() as p:
        browser, context, page = launch_browser(p)
        login_user(page)


        # browser, page = login_user(p, "Test", "User")

        # Determine the operating system and choose the appropriate modifier key
        if platform.system() == "Darwin":
            modifier_key = 'Meta'  # Command key
        else:
            modifier_key = 'Control'  # Control key for Windows/Linux

        page.keyboard.down(modifier_key)
        page.keyboard.press('KeyD')
        page.keyboard.up(modifier_key)

        label1 = page.get_by_text("Release options").first
        label2 = page.get_by_text("Testing preferences").first

        expect(label1).to_be_visible(timeout=100)
        expect(label2).to_be_visible(timeout=100)

        browser.close()