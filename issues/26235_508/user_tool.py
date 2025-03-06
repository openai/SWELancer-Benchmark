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



EXPENSIFY_URL = "http://localhost:8082/"


EMAIL_USERNAME = "naturesv057@gmail.com"
EMAIL_PASSWORD = ""


EMAIL_USERNAME_POSTFIX = "26235_4"


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

    clear_inbox(EMAIL_USERNAME, EMAIL_PASSWORD)

    page.goto(EXPENSIFY_URL)


    page.get_by_role("textbox", name="Phone or email").fill(email)
    page.locator("div", has_text="Continue").last.click()
    

    otp = get_otp_from_email(EMAIL_USERNAME, EMAIL_PASSWORD)
    

    page.keyboard.type(otp)

def test_the_issue():
    """
    Demonstrate the Expensify app email login verification.
    """
    from utils.trace_cleaner import trace_cleaner
    with sync_playwright() as pw:
        browser, context, page = launch_browser(pw)
        try:
            context.tracing.start(screenshots=True, snapshots=True, sources=True)


            email = generate_user_email()
            LOGGER.info("User email %s", email)
            login_user(page, email)
            page.wait_for_timeout(5000)

            LOGGER.info("User logged in successfully")
            
            page.route('**/*', lambda route: route.abort())
            page.locator('div[aria-label="Send message (Floating action)"]').last.click()
            page.wait_for_timeout(1000)
            page.locator('text="Request money"').click()
            page.wait_for_timeout(1000)
            page.locator('text="Manual"').last.click()
            page.wait_for_timeout(1000)
            page.locator('div[aria-label="Select a currency"]').last.click()
            page.wait_for_timeout(1000)
            page.locator('div[aria-label="AED - AED"]').last.click()
            page.wait_for_timeout(2000)
            page.locator('input[placeholder="0"]').fill("200")
            page.wait_for_timeout(1000)
            page.keyboard.press("Enter")
            page.wait_for_timeout(1000)
            page.locator('input[aria-label="Name, email, or phone number"]').fill("test1@gmail.com")
            page.wait_for_timeout(1000)
            page.locator('div[aria-label="test1@gmail.com"]').last.click()
            page.wait_for_timeout(1000)
            page.locator('div', has_text="Request").last.click()
            page.wait_for_timeout(1000)
            page.locator('div', has_text="owes:").last.click()
            page.wait_for_timeout(1000)
            page.locator('div', has_text="Cash").last.click()

            page.wait_for_timeout(1000)
            chat_messages = page.locator('div[aria-label="List of chat messages"]').last
            opacity_half = chat_messages.locator('div[class="css-view-175oi2r"][style="opacity: 0.5;"]')
            opacity_half_count = opacity_half.count()
            assert opacity_half_count == 4
            page.wait_for_timeout(2000)
        except Exception as e:

            raise e
        finally:

            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            context.close()
            browser.close()
