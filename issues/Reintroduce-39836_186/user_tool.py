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
from utils.trace_cleaner import trace_cleaner


# Expensify app URL
EXPENSIFY_URL = "https://dev.new.expensify.com:8082/"

# Email login credentials
EMAIL_USERNAME = "naturesv057@gmail.com"
EMAIL_PASSWORD = "hyjk ilxi pnom oret"

# Email username postfix
EMAIL_USERNAME_POSTFIX = "39836_2"


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
        slow_mo=2000
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


def test_composer():
    with sync_playwright() as p:
        browser, context, page = launch_browser(p)
        # Start recording trace
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        try:
            #Step 1: Login user1
            email = generate_user_email()
            LOGGER.info("User email %s", email)
            login_user(page, email)
            page.wait_for_timeout(5000)

            LOGGER.info("User logged in successfully")

            # Start personal chat
            page.get_by_label("Start chat (Floating action)").click()
            page.get_by_label("Start chat", exact=True).click()
            page.get_by_test_id("selection-list-text-input").fill(email)
            page.get_by_test_id("selection-list").get_by_label("john doe (you)").click()
            page.wait_for_timeout(1000)

            # Type some text
            page.keyboard.type("Line 1")

            # Simulate Shift + Enter
            page.keyboard.down('Shift')
            page.keyboard.press('Enter')
            page.keyboard.up('Shift')

            # Type the next line of text
            page.keyboard.type("Line 2")
            
            # Simulate Shift + Enter again
            page.keyboard.down('Shift')
            page.keyboard.press('Enter')
            page.keyboard.up('Shift')

            page.wait_for_timeout(2000)

            # Retrieve the content of the contenteditable div and assert it matches the entered text
            content = page.evaluate('''() => {
                const paragraphs = document.querySelectorAll("div[role='textbox'][aria-placeholder='Write something...'] p");
                return Array.from(paragraphs).map(p => p.innerText).join("\\n");
            }''').replace("\n\n", "\n")
            
            # Perform the check
            assert content == "Line 1\nLine 2\n", f"Expected 'Line 1\nLine 2\n' but got '{content}'"
        except Exception as e:
            raise e
        finally:
            # Stop tracing and export trace on both success and failure
            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
