import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
import pytest
import os
import random
from playwright.sync_api import sync_playwright, Page, expect
import logging
import email
import imaplib
import sys
from utils.trace_cleaner import trace_cleaner

EXPENSIFY_URL = "https://dev.new.expensify.com:8082/"

EMAIL_USERNAME = "turingsampleopen@gmail.com"
EMAIL_PASSWORD = ""

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

    if page.get_by_text("Track and budget expenses").is_visible():

        page.get_by_label("Track and budget expenses").click()
        page.get_by_role("textbox", name="First name").fill(first_name)
        page.get_by_role("textbox", name="Last name").fill(last_name)
        page.get_by_role("button", name="Continue").click()

        try:
            page.get_by_role("button", name="Back").first.click(timeout=3000)
        except (AssertionError, TimeoutError):
            pass


@pytest.fixture
def setup_playwright(request):
    width = getattr(request, "param", {}).get("width", 1280)
    height = getattr(request, "param", {}).get("height", 720)

    playwright = sync_playwright().start()

    browser = playwright.chromium.launch(
        headless=True, args=["--ignore-certificate-errors", "--disable-web-security",
                "--disable-features-IsolateOrigins,site-per-process"]
    )

    context = browser.new_context(viewport={"width": width, "height": height})
    page = context.new_page()

    yield page


    browser.close()
    playwright.stop()

@pytest.mark.parametrize(
    "setup_playwright",
    [{"width": 1280, "height": 720}],
    indirect=True,
)
def test_export_onyx_state(setup_playwright):
    page = setup_playwright


    page.context.tracing.start(
        title="test_export_onyx_state",
        screenshots=True,
        snapshots=True
    )

    try:
        login_user(page)

        page.locator('button[aria-label="My settings"]').click()
        page.locator('div[aria-label="Troubleshoot"]').click()

        troubleshoot_div = page.locator('div[data-testid="TroubleshootPage"]')
        export_onyx_state_div = troubleshoot_div.locator(
            'div:text("Export Onyx State")', has_text="Export Onyx State"
        )

        assert export_onyx_state_div.is_visible(), "Export Onyx State div is not visible"

        with page.expect_download() as download_info:
            export_onyx_state_div.click()

        download = download_info.value
        download_path = download.path()

        assert download_path is not None, "No file was downloaded"

        file_size = os.path.getsize(download_path)

        assert file_size != 0, "Empty file download for authentication codes!"
    except Exception as e:
        raise e
    finally:

        trace_path = "/app/expensify/user_tool/output_browser1.zip"
        page.context.tracing.stop(path=trace_path)
        trace_cleaner(trace_path)
