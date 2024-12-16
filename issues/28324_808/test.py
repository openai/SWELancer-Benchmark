import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import email
import imaplib
import os
import re
import time
from email.header import decode_header

from playwright.sync_api import Page, TimeoutError, expect, sync_playwright

NOW = int(time.time())
EMAIL_USERNAME = "xecuycismfsga"
EMAIL_ALIAS = "lmpleo"
USER_EMAIL = f"{EMAIL_USERNAME}+{EMAIL_ALIAS}@gmail.com"
PASSWORD = "uwgb zzoc cofa kaaq"
SLOW_MO: int | None = 500
CACHED: bool = True
PROXY_URL = os.getenv("PROXY_URL")
NEW_DOT_URL = "https://dev.new.expensify.com:8082/"


def get_magic_code(
    user_email: str = USER_EMAIL,
    password: str = PASSWORD,
    current_timestamp: int = NOW,
    retries=3,
    delay=8,
    slow_mo: int | None = SLOW_MO,
    cached: bool = CACHED,
):
    if cached:
        return "123456"
    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    imap.login(user_email, password)

    additional_delay = (slow_mo / 1000) if slow_mo else 0
    total_delay = delay + additional_delay

    for _attempt in range(retries):
        print(f"Attempt {_attempt}")

        # Don't wait on the first attempt
        if _attempt > 0:
            print(f"Waiting {total_delay} seconds before next attempt...")
            time.sleep(total_delay)

        imap.select("inbox")
        status, messages = imap.search(
            None, '(UNSEEN SUBJECT "Expensify magic sign-in code:")'
        )

        if status == "OK":
            email_ids = messages[0].split()

            if email_ids:
                latest_email_id = email_ids[-1]
                status, msg_data = imap.fetch(latest_email_id, "(RFC822)")

                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])

                        # Get email timestamp and convert to UTC
                        email_date = msg.get("Date")
                        email_timestamp = email.utils.mktime_tz(
                            email.utils.parsedate_tz(email_date)
                        )

                        # Convert current_timestamp to UTC
                        current_utc = time.time()

                        # Mark the email as seen so we don't process it again
                        imap.store(latest_email_id, "+FLAGS", "\\Seen")

                        print(
                            f"Email time: {email_timestamp}, Current time: {current_utc}"
                        )

                        # If email is too old, wait and try again
                        if email_timestamp < current_timestamp:
                            print(
                                f"Found old email from {email_date}, waiting for new one..."
                            )
                            break  # Break the response_part loop

                        subject, encoding = decode_header(msg["Subject"])[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding or "utf-8")

                        match = re.search(
                            r"Expensify magic sign-in code: (\d+)", subject
                        )
                        if match:
                            code = match.group(1)
                            imap.logout()
                            return code

    imap.logout()
    print("Max retries reached. Email not found.")
    return None


def create_user(page: Page, firstname: str = "User", lastname: str = EMAIL_ALIAS):
    page.get_by_role("button", name="Join").click()

    # Update profile
    page.get_by_text("Track and budget expenses").click()
    page.get_by_role("button", name="Continue").last.click()
    page.get_by_role("textbox", name="First name").fill(firstname)
    page.get_by_role("textbox", name="Last name").fill(lastname)

    try:
        page.get_by_role("button", name="Continue").click(timeout=2000)
    except TimeoutError:
        pass

    try:
        page.get_by_role("button", name="Get Started").click(timeout=200)
    except TimeoutError:
        pass


def login(page: Page):
    # get current timestamp
    magic_code = get_magic_code()

    if magic_code is None:
        raise ValueError("Failed to retrieve magic code")
    page.get_by_role("textbox").fill(magic_code)


def login_or_create_user(
    page: Page,
    user_email: str = USER_EMAIL,
):
    page.get_by_test_id("username").fill(user_email)
    page.get_by_role("button", name="Continue").click()

    try:
        page.get_by_role("button", name="Join").wait_for(state="visible", timeout=2000)
        create_user(page)
    except TimeoutError:
        login(page)


def test_lhn_popup():
    with sync_playwright() as p:
        # Launch chromium and open new page
        browser = p.chromium.launch(
            headless=True,
            slow_mo=SLOW_MO,
            proxy={"server": PROXY_URL} if PROXY_URL else None,
            args=[
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
            ],
        )
        context = browser.new_context()
        page = context.new_page()

        page.goto(NEW_DOT_URL)

        # create user
        login_or_create_user(page)

        # Create Distance Expense
        personal_chat = page.locator(
            'button[aria-label="Navigates to a chat"]:has-text("(you)")'
        ).first
        personal_chat.click()  # Open own chat
        page.get_by_role("textbox").fill("Hello")  # Focus the input field
        personal_chat.click(button="right")  # open chat popup
        page.get_by_role("textbox").fill("Hello world")  # continue typing
        page.get_by_role("textbox").press("Enter")  # Send message

        page.get_by_role("textbox").press("ArrowUp")  # Edit last message
        page.locator("#messageEditInput").fill("\n")
        page.locator("#messageEditInput").press("Enter")

        delete_button_visible = page.get_by_role("button", name="Delete").is_visible()
        cancel_button_visible = page.get_by_role("button", name="Cancel").is_visible()

        if delete_button_visible and cancel_button_visible:
            # Popup menu should not be visible at this point
            expect(page.get_by_label("Mark as unread")).not_to_be_visible()
            expect(page.get_by_label("Unpin")).not_to_be_visible()
            expect(page.get_by_label("Copy Onyx data")).not_to_be_visible()

        # ---------------------
        context.close()
        browser.close()
