import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
import re, time
from datetime import datetime, timezone
from email.header import decode_header

import imaplib, pytest
import email
import re
import random
from utils.trace_cleaner import trace_cleaner


NEWDOT_URL = "http://localhost:8082/"
EMAIL = "f2139887@gmail.com"
PASSWORD = ""


def generate_random_email():
    return f"f2139887+46784@gmail.com"


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
                print("Email doesn't match conditions.  Retrying...")
            else:
                print("No unread emails found with the subject. Retrying...")
        else:
            print("Failed to retrieve emails. Retrying...")
        time.sleep(delay)

    imap.logout()
    print("Max retries reached. Email not found.")
    return None


def login_user_ND_with_magiccode(user_email, password, page):
    page.goto(NEWDOT_URL)

    page.locator('input[type="email"]').fill(user_email)
    page.locator("div:nth-child(3) > div:nth-child(2) > div > div > div > .css-view-175oi2r").click()

    page.wait_for_timeout(5000)

    magic_code = "123456"
    
    page.locator('input[autocomplete="one-time-code"]').fill(magic_code)
    page.wait_for_timeout(500)
    


def test_issue_24642():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="chrome",
            headless=True,
            args=[
                "--ignore-certificate-errors",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process"
            ],
            proxy={"server": "http://localhost:8080"},
            slow_mo=500
        )

        context_args = {}
        context_args["geolocation"] = {"latitude": 37.7749, "longitude": -122.4194}
        context_args["permissions"] = ["geolocation"]
        context_args["ignore_https_errors"] = True

        context = browser.new_context(**context_args)
        # Start tracing with screenshots, snapshots and sources
        context.tracing.start(screenshots=True, snapshots=True, sources=True)

        page = context.new_page()
        first_user_email = generate_random_email()

        try:
            login_user_ND_with_magiccode(first_user_email, PASSWORD, page)
            page.wait_for_timeout(2000)
            context.set_offline(True)
            page.get_by_label("My settings").click()
            page.get_by_text("Profile").click()
            page.get_by_text("Personal details").click()
            try:
                page.get_by_role("button", name="Back").click(timeout=10000)
            except Exception as e:
                pytest.fail("Test failed due to an exception")
        finally:
            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            context.tracing.stop(path=trace_path)
            trace_cleaner(trace_path)

            context.close()
            browser.close()


if __name__ == "__main__":
    test_issue_24642()