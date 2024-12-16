import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

"""
Tests for the issue: https://github.com/Expensify/App/issues/29173
"""

import time
from playwright.sync_api import expect, sync_playwright
import random

import re


USER_NAME = "xecuycismfsga+45609"
USER_EMAIL = f"{USER_NAME}@gmail.com"
PASSWORD = "uwgb zzoc cofa kaaq"


import logging
import email
import imaplib
import sys



EXPENSIFY_URL = "https://dev.new.expensify.com:8082/"


EMAIL_USERNAME = f"xecuycismfsga+45619@gmail.com"
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
        return '123456'
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


def login_user(page, email= EMAIL_USERNAME, password= EMAIL_PASSWORD, first_name="John", last_name="Doe"):
    """
    Log into the Expensify app.
    """
    # Clear the email inbox
    clear_inbox(email, password)
    # Open the Expensify app
    # page.goto(EXPENSIFY_URL)
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
        otp_code = get_otp_from_email(email, password)
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





# Expensify app URL
EXPENSIFY_URL = "https://dev.new.expensify.com:8082/"

def generate_random_email():
    """
    Utility to generate a random email address.
    """
    username = "jellystarfish99"
    timestamp = random.randint(1, 2**20)
    return f"{username}+{random.randint(1, 2**20)}@gmail.com"


def launch_app(pw):
    """
    Launch the Expensify app.
    """
    browser = pw.chromium.launch(headless=True, args=[
                "--ignore-certificate-errors",
                "--disable-web-security",
                "--disable-features-IsolateOrigins,site-per-process"
                ], slow_mo = 1000)
    context = browser.new_context()
    page = context.new_page()
    page.goto(EXPENSIFY_URL)
    return browser, context, page


def login_user_old(page, email, first_name="Jhon", last_name="Doe"):
    """
    Login to the Expensify app and complete the onboarding.
    """
    # Login user
    page.locator("input[type='email']").fill(email)
    page.get_by_role("button", name="Continue").click()
    page.get_by_role("button", name="Join").click()

    # Complete onboarding
    page.get_by_text("Track and budget expenses").click()
    page.locator("input[name='fname']").fill(first_name)
    page.locator("input[name='lname']").fill(last_name)
    page.get_by_role("button", name="Continue").click()


def test_new_line_for_first_interaction_between_two_users():
    """
    Verify that when User A sends a message to User B (first iteraction), the message is displayed juest after a new line.
    """
    with sync_playwright() as pw:
        
        # User A (sender): Launch the app and login
        email_a = generate_random_email()
        browser_a, context_a, page_a = launch_app(pw)
        login_user(page_a, USER_EMAIL, PASSWORD, "User A", "Sender")
        
        # User B (receiver): Launch the app and login
        email_b = generate_random_email()
        browser_b, context_b, page_b = launch_app(pw)
        login_user(page_b, EMAIL_USERNAME, PASSWORD, "User B", "Receiver")
        # login_user_(page_b, EMAIL_USERNAME, "User B", "Receiver")


       # Click on "Create" button (+)
        page_a.get_by_label("Start chat (Floating action)").click()
        
        # Click on "Start chat" button
        page_a.get_by_text("Start chat").click()
        
        # Input the email of User B (receiver)
        expect(page_a.get_by_test_id("selection-list-text-input")).to_be_visible()
        page_a.get_by_test_id("selection-list-text-input").fill(EMAIL_USERNAME)
        page_a.wait_for_timeout(2000)  # Wait for the email to be validated
        
        # Add User B (receiver) to the chat
        expect(page_a.get_by_role("button", name="Add to group")).to_be_visible()
        page_a.get_by_role("button", name="Add to group").click()  # Select User B
        page_a.get_by_role("button", name="Next").click()  # Click on "Next" button
        
        # Create the chat
        expect(page_a.get_by_role("button", name="Start group")).to_be_visible()
        page_a.get_by_role("button", name="Start group").click()
        page_a.wait_for_timeout(1000)  # Wait for the chat to be created
        
        # Send a message from User A to User B
        expect(page_a.get_by_role("textbox")).to_be_visible()
        page_a.get_by_role("textbox").fill("Hello, User B!")
        page_a.get_by_role("textbox").press("Enter")
        
        # User B expects to see the message from User A
        expect(page_b.locator('[data-testid="DisplayNamesWithTooltip"]:text("User A, User B")')).to_be_visible(timeout=15000)
        page_b.locator('[data-testid="DisplayNamesWithTooltip"]:text("User A, User B")').click()

        # Assert that the message is displayed just after a new line
        page_b.wait_for_timeout(4000) # Wait for the message to be displayed
        assert page_b.locator('div[aria-label="New message line indicator"]').count() == 1, "New line indicator is not visible"

        # Close the browser
        context_a.close()
        browser_a.close()
        context_b.close()
        browser_b.close()

