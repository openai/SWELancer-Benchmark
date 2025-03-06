import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
from playwright._impl._page import Page
from playwright.sync_api import sync_playwright, expect
import logging
import email
import imaplib
import sys
from utils.trace_cleaner import trace_cleaner

EXPENSIFY_URL = "https://dev.new.expensify.com:8082/"


EMAIL_USERNAME = "expensifytesting1@gmail.com"
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


first_name = "Alice"
last_name = "Aliceoglu"


def generate_random_email():
    timestamp = int(time.time())
    return f"myttestusermail+{timestamp}@gmail.com"

def login_user_old(page: Page) -> None:

    username_input = page.get_by_test_id("username")
    username_input.click()

    username_input.fill("myttestusermail+1733384655@gmail.com")

    continue_button = page.get_by_role("button", name="Continue")
    continue_button.click()
    

    join_button = page.get_by_role("button", name="Join")
    join_button.click()
    

    track_expenses_text = page.get_by_text("Track and budget expenses")
    track_expenses_text.click()

def enter_user_information(page:Page) -> None:

    first_name_input = page.get_by_role("textbox", name="First name")
    first_name_input.fill(first_name)

    first_name_input.press("Tab")

    last_name_input = page.get_by_role("textbox", name="Last name")
    last_name_input.fill(last_name)
    

    continue_button_after_names = page.get_by_role("button", name="Continue")
    continue_button_after_names.click()

def add_new_member(page, random_mail):
    invite_button = page.get_by_role("button", name="Invite member")
    invite_button.click()
    

    page.get_by_test_id("selection-list-text-input").click()    
    page.get_by_test_id("selection-list-text-input").fill(random_mail)
    page.wait_for_timeout(500)
    

    invited_member_button = page.get_by_role("button", name=random_mail).first
    invited_member_button.click()
    
    next_button = page.get_by_role("button", name="Next")
    next_button.click()
    
    page.get_by_test_id("WorkspaceInviteMessagePage").get_by_role("button", name="Invite").click()
    page.wait_for_timeout(2000)

def reproduce_scenario(page: Page) -> None:

    page.locator('button[aria-label="My settings"]').click()
    page.locator('div[aria-label="Workspaces"]').click()
    page.get_by_role('button', name='New workspace').nth(0).click()


    member_button = page.get_by_text("Members")
    member_button.click()


    random_mail1 = "myttestusermail+1733342847@gmail.com"
    add_new_member(page, random_mail1)


    random_mail2 = "myttestusermail+1733342853@gmail.com"
    add_new_member(page, random_mail2)
    page.wait_for_timeout(1000)    

    page.locator("div:nth-child(3) > div > div:nth-child(4) > div").click()
    

    page.get_by_role("button", name="Remove from workspace").click()


    popup_message = page.get_by_text(f"{random_mail2} is an approver in this workspace")
    print(popup_message)
    expect(popup_message).not_to_be_visible()

def test_popup_message_on_removing_member_from_ws() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=["--ignore-certificate-errors", "--disable-web-security",
                "--disable-features-IsolateOrigins,site-per-process"], slow_mo=500)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()


        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        try:

            login_user(page)



            

            reproduce_scenario(page)

            time.sleep(1)
        finally:

            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")

            context.close()
            browser.close()
