import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
import pytest
from playwright.sync_api import sync_playwright, expect
import imaplib
import email
from email.header import decode_header
import re
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page

from utils.trace_cleaner import trace_cleaner


def generate_random_email(base_email="testerbro7077@gmail.com"):
    timestamp = int("28077")
    email_user, domain = base_email.split('@')
    return f"{email_user}+{timestamp}@{domain}"


def get_magic_code(user_email, password, retries=5, delay=10):
    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    imap.login(user_email, password)

    for attempt in range(retries):
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
                        if match:
                            code = match.group(1)
                            imap.logout()
                            return code
            else:
                print("No unread emails found with the subject. Retrying...")
        else:
            print("Failed to retrieve emails. Retrying...")

        time.sleep(delay)

    imap.logout()
    print("Max retries reached. Email not found.")
    return None


def login_user(p: PlaywrightContextManager, first_name="Yagna", last_name="Sai") -> tuple[Browser, Page, str]:
    user_email = generate_random_email()
    password = "xqxz mmcb tvkn lpgp"

    browser = p.chromium.launch(headless=True, args=[
        '--disable-web-security',
        '--disable-features=IsolateOrigins,site-per-process'
    ])
    context = browser.new_context()
    page = context.new_page()

    page.goto('https://dev.new.expensify.com:8082/')
    phone_or_email_input = page.locator('input[type="email"]')
    expect(phone_or_email_input).to_be_visible()
    phone_or_email_input.fill(user_email)

    continue_button = page.locator('button[tabindex="0"]')
    expect(continue_button).to_be_visible()
    continue_button.click()

    page.wait_for_timeout(1000)

    magic_code = "123456"

    validate_code_input = page.locator('input[data-testid="validateCode"]')
    expect(validate_code_input).to_be_visible()
    validate_code_input.fill(magic_code)

    page.wait_for_timeout(1000)

    return browser, page, user_email


def check_name(page):
    page.locator('button[aria-label="My settings"]').click()
    time.sleep(1)

    page.click('//div[contains(text(), "Display name")]')
    page.wait_for_timeout(1000)

    page.locator('button[aria-label="Back"]').click()
    page.wait_for_timeout(1000)

    page.locator('div[aria-label="Sign out"]').click()
    page.wait_for_timeout(1000)


def login_user2(p: PlaywrightContextManager, first_name="Yagna", last_name="Sai") -> tuple[Browser, Page, str]:
    user_email = generate_random_email()
    password = "xqxz mmcb tvkn lpgp"

    browser = p.chromium.launch(headless=True, args=[
        '--disable-web-security',
        '--disable-features=IsolateOrigins,site-per-process'
    ])
    context = browser.new_context()
    page = context.new_page()

    page.goto('https://dev.new.expensify.com:8082/settings/profile/display-name')
    phone_or_email_input = page.locator('input[type="email"]')
    expect(phone_or_email_input).to_be_visible()
    phone_or_email_input.fill(user_email)

    continue_button = page.locator('button[tabindex="0"]')
    expect(continue_button).to_be_visible()
    continue_button.click()

    page.wait_for_timeout(1000)

    magic_code = "123456"

    validate_code_input = page.locator('input[data-testid="validateCode"]')
    expect(validate_code_input).to_be_visible()
    validate_code_input.fill(magic_code)

    page.wait_for_timeout(1000)

    return browser, page, user_email


def check_name2(page):
    page.get_by_text("Display name").click()
    page.wait_for_timeout(1000)

    page.locator('button[aria-label="Back"]').click()
    page.wait_for_timeout(1000)

    page.locator('button[aria-label="Inbox"]').click()
    page.wait_for_timeout(1000)

    first_name_input = page.locator('input[aria-label="First name"]')
    expect(first_name_input).to_have_value("Yagna")
    page.wait_for_timeout(1000)

    last_name_input = page.locator('input[aria-label="Last name"]')
    expect(last_name_input).to_have_value("Sai")
    page.wait_for_timeout(1000)


@pytest.mark.parametrize("first_name, last_name", [("Yagna", "Sai")])
def test_run(first_name: str, last_name: str) -> None:
    with sync_playwright() as playwright:
        # First browser session with tracing
        try:
            browser1, page1, user_email1 = login_user(playwright, first_name, last_name)
            context1 = page1.context
            context1.tracing.start(screenshots=True, snapshots=True, sources=True)
            print(f"Logged in with email: {user_email1}")
            check_name(page1)
        finally:
            context1.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            browser1.close()

        # Second browser session with tracing
        try:
            browser2, page2, user_email2 = login_user2(playwright, first_name, last_name)
            context2 = page2.context
            context2.tracing.start(screenshots=True, snapshots=True, sources=True)
            check_name2(page2)
        finally:
            context2.tracing.stop(path="/app/expensify/user_tool/output_browser2.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser2.zip")
            browser2.close()


if __name__ == "__main__":
    pytest.main([__file__])
