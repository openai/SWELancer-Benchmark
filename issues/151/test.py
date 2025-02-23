import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page
import re
import imaplib
import email
from email.header import decode_header
from datetime import datetime, timezone

EMAIL_USERNAME = "aliceoglualice@gmail.com"
EMAIL_PASSWORD = "cfpy ofxm lcmq aeta"


def get_magic_code(user_email, password, since=None, retries=5, delay=10):

    if since is None:
        since = datetime.now(timezone.utc).replace(second=0, microsecond=0)

    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    

    imap.login(user_email, password)

    for _ in range(retries):

        imap.select("inbox")
        status, messages = imap.search(None, '(UNSEEN SUBJECT "Expensify magic sign-in code:")')

        if status == "OK":
            email_ids = messages[0].split()

            if email_ids:

                latest_email_id = email_ids[-1]
                status, msg_data = imap.fetch(latest_email_id, "(RFC822)")

                for response_part in msg_data:
                    if isinstance(response_part, tuple):

                        msg = email.message_from_bytes(response_part[1])
                        subject, encoding = decode_header(msg["Subject"])[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding or "utf-8")

                        match = re.search(r"Expensify magic sign-in code: (\d+)", subject)
                        email_date = email.utils.parsedate_to_datetime(msg["Date"])
                        if match and email_date >= since:

                            code = match.group(1)
                            imap.logout()
                            return code
                print("Email doesn't match conditions. Retrying...")
            else:
                print("No unread emails found with the subject. Retrying...")
        else:
            print("Failed to retrieve emails. Retrying...")
        time.sleep(delay)


    imap.logout()
    print("Max retries reached. Email not found.")
    return None


def login_user(p: PlaywrightContextManager, first_name="Milan", last_name="T") -> tuple[Browser, Page, str]:

    browser = p.chromium.launch(headless=True, args=[
        "--disable-web-security",
        "--disable-features=IsolateOrigins,site-per-process",
        "--ignore-certificate-errors"
    ])
    page = browser.new_page()
    user_email = EMAIL_USERNAME


    page.goto('https://dev.new.expensify.com:8082/') 


    page.get_by_test_id("username").fill(user_email)
    page.get_by_role("button", name="Continue").click()

    try:
        expect(page.get_by_test_id("SignInPage").get_by_test_id("validateCode")).to_be_visible(timeout=5000)
    except (AssertionError, TimeoutError):

        page.get_by_test_id("SignInPage").get_by_role("button", name="Join").click()
    else:

        otp_code = "123456" #get_magic_code(EMAIL_USERNAME, EMAIL_PASSWORD)
        otp_input = page.locator('input[autocomplete="one-time-code"]')
        otp_input.fill(otp_code)


    try:
        expect(page.get_by_text("What do you want to do today?")).to_be_visible(timeout=5000)
    except (AssertionError, TimeoutError):
        pass
    else:

        page.get_by_label("Track and budget expenses").click()
        page.get_by_role("textbox", name="First name").fill(first_name)
        page.get_by_role("textbox", name="Last name").fill(last_name)
        page.get_by_role("button", name="Continue").click()

    return browser, page, user_email


def test_edit_box_and_compose_box_alignment():
    with sync_playwright() as p:

        browser, page, user_email = login_user(p)


        personal_chat = page.get_by_text(f"Milan T (you)").first
        expect(personal_chat).to_be_visible()
        personal_chat.click()


        message_one = page.get_by_role("textbox").fill("My Message")
        page.get_by_role("textbox").press("Enter")
        page.wait_for_timeout(500)


        message_two = page.get_by_role("textbox").fill("My Second Message")
        page.get_by_role("textbox").press("Enter")
        page.wait_for_timeout(500)


        message_three = page.get_by_role("textbox").fill("My Third Message")
        page.get_by_role("textbox").press("Enter")
        page.wait_for_timeout(500)

        message_three = page.locator('span', has_text="My Third Message")
        message_three.click(button="right")

        option_menu = page.locator('div[aria-label="Edit comment"]', has_text="Edit comment")

        option_menu.click()
        page.wait_for_timeout(2000)


        element1 = page.locator("button[aria-label='Close']")
        element2 = page.locator("button[aria-label='Create']").nth(1)


        element1_x = element1.bounding_box()["x"]
        element2_x = element2.bounding_box()["x"]


        assert element1_x == element2_x, f"Elements are not vertically aligned. Element1 x: {element1_x}, Element2 x: {element2_x}"

        browser.close()
