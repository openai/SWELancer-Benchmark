import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

"""
Tests for the issue: https://github.com/Expensify/App/issues/44165
"""

import email
import imaplib
import logging
import sys
import time

from playwright.sync_api import TimeoutError, expect, sync_playwright


EXPENSIFY_URL = "https://dev.new.expensify.com:8082/"


EMAIL_USERNAME = "expensifytesting1@gmail.com"
EMAIL_PASSWORD = "redx tbmr hzpc rbzr"


EMAIL_USERNAME_POSTFIX = "44165.1"


logging.basicConfig(level=logging.INFO, stream=sys.stdout, format="%(message)s")
LOGGER = logging.getLogger(__name__)


def generate_user_email(user_id=None):
    """
    Generate an email address for a user login.
    """
    temp = EMAIL_USERNAME.rsplit("@", 1)
    username = temp[0].strip()
    domain = temp[1].strip()
    return f"{username}+{EMAIL_USERNAME_POSTFIX}{user_id or ""}@{domain}"


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
    otp_code = '123456'
    return otp_code
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


def login_user(page, email, first_name="John", last_name="Doe"):
    """
    Log into the Expensify app.
    """

    clear_inbox(EMAIL_USERNAME, EMAIL_PASSWORD)

    page.goto(EXPENSIFY_URL)

    page.get_by_test_id("username").fill(email)
    page.get_by_role("button", name="Continue").click()

    try:
        expect(page.get_by_test_id("SignInPage").get_by_test_id("validateCode")).to_be_visible(timeout=7000)
    except (AssertionError, TimeoutError):

        page.get_by_test_id("SignInPage").get_by_role("button", name="Join").click()
    else:

        otp_code = get_otp_from_email(EMAIL_USERNAME, EMAIL_PASSWORD)
        page.get_by_test_id("SignInPage").get_by_test_id("validateCode").fill(otp_code)

    try:
        page.get_by_test_id("SignInPage").get_by_role("button", name="Sign in").click()

        expect(page.get_by_text("What do you want to do today?")).to_be_visible(timeout=10000)
    except (AssertionError, TimeoutError):
        pass
    else:

        page.get_by_label("Track and budget expenses").click()
        page.get_by_role("textbox", name="First name").fill(first_name)
        page.get_by_role("textbox", name="Last name").fill(last_name)
        page.get_by_role("button", name="Continue").click()

        try:
            page.get_by_role("button", name="Back").first.click(timeout=3000)
        except (AssertionError, TimeoutError):
            pass

    try:
        page.get_by_role("button", name="Close").click(timeout=3000)
    except (AssertionError, TimeoutError):
        pass

    expect(page.get_by_test_id("BaseSidebarScreen")).to_be_visible(timeout=10000)


def test_submit_expense_header_displays_on_reload_after_selecting_waypoint_menu():
    """
    Verify that the Submit expense menu header displays even after reloading.
    """
    with sync_playwright() as pw:

        email = generate_user_email()
        LOGGER.info("User email: %s", email)
        LOGGER.info("Launch the app in the mobile view")
        browser, context, page = launch_browser(pw, device="Pixel 7")
        login_user(page, email)


        LOGGER.info("Start a Submit expense request")
        page.get_by_role("button", name="Start chat (Floating action)").click()
        page.get_by_role("menuitem", name="Submit expense").click()


        LOGGER.info("Switch to Distance tab and click on the Start location")
        page.get_by_test_id("IOURequestStartPage").get_by_role("button", name="Distance").click()
        page.get_by_role("menuitem", name="Start").click()


        LOGGER.info("Reload the page")
        page.reload()


        LOGGER.info("Go back")
        page.get_by_label("Back").click()


        page.wait_for_timeout(2000)


        LOGGER.info("Verify that the Submit expense menu header is still visible")
        for item in ("Manual", "Scan", "Distance"):
            assert_message = f"'{item}' should be visible in the header"
            expect(page.get_by_label(item), assert_message).to_be_visible(timeout=3)


        context.close()
        browser.close()

