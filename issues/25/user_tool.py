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
import pytest
from playwright.sync_api import sync_playwright, expect, Page
from utils.trace_cleaner import trace_cleaner


EXPENSIFY_URL = "https://dev.new.expensify.com:8082/"


EMAIL_USERNAME = "naturesv057@gmail.com"
EMAIL_PASSWORD = "hyjk ilxi pnom oret"


EMAIL_USERNAME_POSTFIX = "49298_4"


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

    page.get_by_test_id("username").fill(email)
    page.get_by_role("button", name="Continue").click()


    otp_code = get_otp_from_email(EMAIL_USERNAME, EMAIL_PASSWORD)
    page.get_by_test_id("validateCode").fill(otp_code)

def test():
    with sync_playwright() as p:
        email = generate_user_email()
        LOGGER.info("User email %s", email)
        browser, context, page = launch_browser(p)


        context.tracing.start(screenshots=True, snapshots=True)
        try:
            login_user(page, email)
            page.wait_for_timeout(5000)

            LOGGER.info("User logged in successfully")

            page.locator(
                'button[aria-label="Start chat (Floating action)"][tabindex="0"]'
            ).click()


            page.locator('div[aria-label="Start chat"][role="menuitem"]').click()

            page.locator('input[aria-label="Name, email, or phone number"]').fill(
                "t56826807+13@gmail.com"
            )
            try:
                page.locator('button[aria-label="Employee"]').last.click(timeout=3000)
            except:
                page.get_by_label("t56826807+13@gmail.com").click()
            page.locator('button[aria-label="Employee"]').last.click()

            page.locator('div[aria-label="Private notes"]').last.click()
            page.locator('div[aria-label="Private notes"][role="textbox"]').fill(
                "new line\n" * 100
            )

            page.locator('button[data-listener="Enter"]', has_text="Save").last.click()

            page.locator('div[aria-label="Private notes"]').last.click()

            text = page.locator('div[data-testid="PrivateNotesListPage"]').inner_text()
            print(text)

            page.wait_for_selector('div[data-testid="PrivateNotesListPage"]')
            parent_div = page.locator('div[data-testid="PrivateNotesListPage"]')


            child_with_scroll_y = parent_div.evaluate_handle(
                """parent => {
                const children = parent.querySelectorAll("div");
                return Array.from(children).find(child => {
                    const style = getComputedStyle(child);
                    return style.overflowY === "scroll" || style.overflowY === "auto";
                });
            }"""
            )


            if child_with_scroll_y:
                text = child_with_scroll_y.evaluate("element => element.innerText")
                print(text)
            else:
                raise Exception("No child div with overflow-y set to scroll or auto found.")

            assert (
                "Keep notes about this chat here. You're the only person who can add, edit, or view these notes."
                in text
            ), "The intro text on private notes list stays fixed when it should scroll with the page"
        except Exception as e:
            raise e
        finally:

            context.tracing.stop()
            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            context.tracing.export(trace_path)
            trace_cleaner(trace_path)
