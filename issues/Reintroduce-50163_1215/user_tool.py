import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import email
import imaplib
import re
import time
from email.header import decode_header

from playwright.sync_api import expect, sync_playwright

# Added the trace_cleaner import
from utils.trace_cleaner import trace_cleaner

expensify_email = "totherandomuser+50163@gmail.com"
user_email = "totherandomuser@gmail.com"
password = "umei djwi bfmp jntm"


def mark_inbox_read(user_email, password):
    # Connect to the server
    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    imap.login(user_email, password)

    # Mark all existing unread emails as read in a single command
    imap.select("inbox")
    status, all_emails = imap.search(None, "UNSEEN")
    if status == "OK" and all_emails[0]:
        email_ids = all_emails[0].replace(b" ", b",")
        imap.store(email_ids.decode(), "+FLAGS", "\\Seen")
    imap.logout()
    return


def get_magic_code(user_email, password, retries=5, delay=5):
    # Connect to the server
    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    imap.login(user_email, password)

    # Retry logic for finding the magic code
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

                        # Search for the magic code in the subject
                        match = re.search(r"Expensify magic sign-in code: (\d+)", subject)
                        if match:
                            code = match.group(1)
                            imap.logout()
                            return code
            else:
                print("No unread emails found with the subject. Retrying...")
        else:
            print("Failed to retrieve emails. Retrying...")

        # Wait for the specified delay before trying again
        time.sleep(delay)

    imap.logout()
    print("Max retries reached. Email not found.")
    return None


def login(p, if_phone=False, first_name="John", last_name="Cena"):
    # step 1: Login
    permissions = ["clipboard-read", "clipboard-write"]
    browser = p.chromium.launch(
        headless=True,
        args=["--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"],
    )

    if if_phone:
        phone = p.devices["iPhone 12 Pro"]
        context = browser.new_context(**phone, permissions=permissions, reduced_motion="no-preference")
    else:
        context = browser.new_context()

    page = context.new_page()

    page.goto("https://dev.new.expensify.com:8082")

    # step 0: mark the inbox read
    mark_inbox_read(user_email, password)

    # Step 1: Enter username and continue
    page.get_by_test_id("username").click()
    page.get_by_test_id("username").fill(expensify_email)
    page.get_by_role("button", name="Continue").click()

    # Step 2: Mark Inbox read and then get the magic code.
    # magic_code = get_magic_code(user_email, password, retries=3, delay=10)
    # Use any value for the magic code while replaying
    magic_code = "123456"

    validate_code_input = page.locator('input[name="validateCode"]')
    expect(validate_code_input).to_be_visible()
    validate_code_input.fill(magic_code)
    page.wait_for_timeout(1000)

    return browser, page, context


def test():
    with sync_playwright() as p:
        # Step 1: Login
        browser, page, context = login(p, False)
        # Start tracing
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        try:
            # Step 2: Go to Search Tab and click on rename.
            page.get_by_test_id("CustomBottomTabNavigator").get_by_label("Search").click()
            page.get_by_text("type:expense status:all").click()
            page.get_by_label("More").click()
            page.get_by_text("Rename").click()

            # Step 3: validate the close button
            page.wait_for_timeout(2000)
            is_clear_button_visible = False
            if page.get_by_label("Clear").is_visible():
                is_clear_button_visible = True
                print("The 'Clear' button is available.")

            assert is_clear_button_visible == True, "The clear button is not visible, it should be visible!!"
        except Exception as e:
            # We re-raise to ensure the test fails if there's an error
            raise e
        finally:
            # Stop tracing and save
            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            # Clean the trace
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            # Close the browser
            browser.close()