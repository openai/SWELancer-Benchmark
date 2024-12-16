import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from time import time
from playwright.sync_api import sync_playwright, expect
from playwright._impl._page import Page
import imaplib
import email
from email.header import decode_header
import re

from utils.trace_cleaner import trace_cleaner

def launch_app(p, headless=True, device=None, geolocation=None):
    """
    Launch the Expensify app.
    """
    browser = p.chromium.launch(headless=headless,
                args=[
                    '--ignore-certificate-errors',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process',
                ])
    context_args = {}
    if device:
        context_args.update(p.devices[device])
    if geolocation:
        context_args["geolocation"] = geolocation
        context_args["permissions"] = ["geolocation"]
    context = browser.new_context(**context_args)
    page = context.new_page()
    return browser, context, page


def login_with_otp(page: Page, user_email) -> Page:
    # Step 1: Open expensify url
    page.goto('https://dev.new.expensify.com:8082/')

    # Enter email and click continue
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()

    # Check latest mail for 40 seconds for mail with OTP
    code = get_magic_code(page, user_email, "aymv mpce nrvd cvye ", retries=8, delay=5000)
    page.wait_for_timeout(2000)
    code = "123456"
    # Enter OTP
    page.locator('input[autocomplete="one-time-code"]').fill(code)
    # page.locator('button[tabindex="0"]').click()

    return page


def get_magic_code(page, user_email, password, retries=8, delay=5000):

    # Connect to the server
    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    imap.login(user_email, password)

    for _ in range(retries):
        imap.select("inbox")
        status, messages = imap.search(None, '(UNSEEN SUBJECT "sign-in code:")')

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
                        match = re.search(r"sign-in code: (\d+)", subject)
                        if match:
                            code = match.group(1)
                            imap.logout()
                            return code
            else:
                print("No unread emails found with the subject. Retrying...")
        else:
            print("Failed to retrieve emails. Retrying...")

        # Wait for the specified delay before trying again
        page.wait_for_timeout(2000)

    imap.logout()
    print("Max retries reached. Email not found.")
    return None


def test_workspace_no_category():
    with sync_playwright() as p:
        browser, context, page = launch_app(p)
        context.tracing.start(title="Trace for test_workspace_no_category", screenshots=True, snapshots=True)
        try:
            user_email = "bobexpensifytest+1730068043@gmail.com"

            page = login_with_otp(page, user_email)

            personal_chat = page.locator('button[aria-label="Navigates to a chat"]', has_text="Bob T (you)")
            expect(personal_chat).to_be_visible()
            personal_chat.click()

            categorize = page.get_by_text("Categorize it")
            expect(categorize).to_be_visible()
            categorize.click()

            page.wait_for_timeout(3000)

            workspaace_with_no_category_button = page.locator('button[aria-label="Workspace with NO Category"]')
            expect(workspaace_with_no_category_button).not_to_be_visible()
        except Exception as e:
            raise e
        finally:
            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            context.tracing.stop(path=trace_path)
            trace_cleaner(trace_path)
        browser.close()