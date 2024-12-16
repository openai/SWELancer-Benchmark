import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
from playwright.sync_api import sync_playwright, expect
import imaplib
import email
from email.header import decode_header
import re

from utils.trace_cleaner import trace_cleaner

user_email = "totherandomuser@gmail.com"
password = "umei djwi bfmp jntm"


def get_magic_code(user_email, password, retries=5, delay=10):
    # Connect to the server
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
    permissions = ['clipboard-read', 'clipboard-write']
    browser = p.chromium.launch(headless=True, args=[
        '--disable-web-security',
        '--disable-features=IsolateOrigins,site-per-process'
    ])

    if if_phone:
        phone = p.devices['iPhone 12 Pro']
        context = browser.new_context(**phone, permissions=permissions, reduced_motion='no-preference')
    else:
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

    # magic_code = get_magic_code(user_email, password, retries=3, delay=10)
    magic_code = "123456"
    validate_code_input = page.locator('input[name="validateCode"]')
    expect(validate_code_input).to_be_visible()
    validate_code_input.fill(magic_code)

    page.wait_for_timeout(1000)

    return browser, page


def test():
    with sync_playwright() as p:
        browser, page = login(p, False)
        context = page.context
        # Start recording the trace
        context.tracing.start(title="test-trace", screenshots=True, snapshots=True)

        try:
            page.wait_for_timeout(5000)

            # Locate the div containing the specific text and click it
            group_chat = page.get_by_text(f"Totherandomuser's Workspace 2").first
            expect(group_chat).to_be_visible()
            group_chat.click()

            page.wait_for_timeout(1000)

            page.get_by_role("textbox").fill("My Message")
            page.get_by_role("textbox").press("Enter")
            page.wait_for_timeout(1000)

            page.get_by_label("My settings").click()
            page.get_by_label("Preferences").click()
            page.get_by_label("Force offline").click()
            page.locator("#overLayBottomButton").click()
            page.wait_for_timeout(1000)

            message = page.locator('span', has_text="My Message").last
            expect(message).to_be_visible()
            message.click(button="right")
            page.wait_for_timeout(1000)

            # Locate the element using aria-label and click it
            delete_button = page.locator('[aria-label="Delete comment"]').first
            delete_button.click()
            page.get_by_role("button", name="Delete").click()

            page.wait_for_timeout(1000)
            message = page.locator('span', has_text="My Message").last
            expect(message).to_be_visible()
            message.click(button="right")
            page.wait_for_timeout(1000)

            is_unsubscribed = False

            # Check if the "Unsubscribe from thread" element is visible on the page
            unsubscribe_div = page.locator(
                'div[data-selection-scrapper-hidden-element="false"].css-text-146c3p1',
                has_text="Unsubscribe from thread"
            )
            is_unsubscribe_present = unsubscribe_div.is_visible()

            print(is_unsubscribe_present)

            assert is_unsubscribe_present == False, "Unsubscribe from thread Button should not be visible."

        except Exception as e:
            # Stop the trace and save to file even if test fails
            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            raise e
        else:
            # Stop the trace and save to file upon success
            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
        finally:
            browser.close()
