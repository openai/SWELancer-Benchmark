import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
from playwright.sync_api import sync_playwright, expect
import imaplib
import email
from email.header import decode_header
import re

# Import necessary for cleaning traces
from utils.trace_cleaner import trace_cleaner

# Gmail credentials with app-specific password
user_email = "playwright2user+100@gmail.com"
password = "zehr mglm gizg gjcc"

def fetch_verification_code_from_email(user_email, password, retries=5, delay=10):
    # Connect to Gmail using IMAP
    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    imap.login(user_email, password)

    for attempt in range(retries):
        # Select inbox
        imap.select("inbox")
        status, messages = imap.search(
            None, '(UNSEEN SUBJECT "Expensify magic sign-in code")')

        if status == "OK":
            email_ids = messages[0].split()

            if email_ids:
                # Retrieve the most recent email
                latest_email_id = email_ids[-1]
                status, msg_data = imap.fetch(latest_email_id, "(RFC822)")

                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        subject, encoding = decode_header(msg["Subject"])[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding or "utf-8")

                        # If the email is multipart (contains HTML and text), extract the text part
                        if msg.is_multipart():
                            for part in msg.walk():
                                content_type = part.get_content_type()
                                if content_type == "text/plain":
                                    body = part.get_payload(
                                        decode=True).decode()
                                    # Extract the OTP code from the text content
                                    match = re.search(r'\b\d{6}\b', body)
                                    if match:
                                        otp_code = match.group(0)
                                        imap.logout()
                                        return otp_code
                        else:
                            # If the email is not multipart, decode the plain text payload directly
                            body = msg.get_payload(decode=True).decode()
                            match = re.search(r'\b\d{6}\b', body)
                            if match:
                                otp_code = match.group(0)
                                imap.logout()
                                return otp_code
            else:
                print("No unread emails found. Retrying...")
                otp_code = "123456"
                return otp_code
        else:
            print("Failed to retrieve emails. Retrying...")

        # Wait before trying again
        time.sleep(delay)

    imap.logout()
    print("Max retries reached. No email found.")
    return None

def login(page):
    # email address
    email_input = page.locator('input[type="email"]')
    expect(email_input).to_be_visible()
    email_input.fill(user_email)

    # Click "Continue"
    continue_button = page.locator('button[tabindex="0"]')
    expect(continue_button).to_be_visible()
    continue_button.click()

    # Fetch and modify the verification link from the email
    page.wait_for_timeout(4000)

    verification_code = fetch_verification_code_from_email(
        user_email, password)
    # input code
    input_code = page.locator('[autocomplete="one-time-code"]')
    input_code.fill(verification_code)

def test_49894():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,  # Set to False to see the browser
            args=[
                "--disable-web-security",  # Disable CORS (for testing only)
                "--disable-features=IsolateOrigins,site-per-process",
            ]
        )
        context = browser.new_context(ignore_https_errors=True)

        # Start recording trace
        context.tracing.start(
            screenshots=True,
            snapshots=True,
            sources=True
        )

        page = context.new_page()
        try:
            # Go to login page
            page.goto('https://dev.new.expensify.com:8082/')

            login(page)

            # Click on the Settings button
            settings_button = page.locator('button[aria-label="My settings"]')
            settings_button.click()
            page.wait_for_timeout(500)

            # Click on the Workspaces button
            workspaces_button = page.locator('div[aria-label="Workspaces"]')
            expect(workspaces_button).to_be_visible(timeout=100)
            workspaces_button.click()
            page.wait_for_timeout(500)

            # Click on the New Workspace button
            new_workspace_button = page.locator('button[aria-label="New workspace"]')
            expect(new_workspace_button).to_be_visible(timeout=100)
            new_workspace_button.click()
            page.wait_for_timeout(500)

            # Click Back
            back_button = page.locator("[aria-label='Back']").nth(0)
            back_button.click()
            page.wait_for_timeout(500)

            # Click on inbox
            inbox_button = page.locator('button[aria-label="Inbox"]')
            inbox_button.click()

            # Assign task and set title and empty description
            page.get_by_role("button", name="Create").click()
            page.get_by_label("Assign task").click()
            page.get_by_role("textbox", name="Title").fill("title1")
            page.get_by_role("button", name="Next").click()

            # Edit description and type "` `"
            page.get_by_test_id("NewTaskPage").get_by_text("Description").click()
            page.get_by_role("textbox", name="Description (optional)").fill("` `")
            page.get_by_role("button", name="Next").click()

            # Check if this is in markdown
            expect(page.get_by_test_id("NewTaskPage").locator('span')).to_have_text(" ")
            page.wait_for_timeout(2000)

            # Open description and add a space
            page.get_by_test_id("NewTaskPage").get_by_text("Description").click()
            page.get_by_role("textbox", name="Description (optional)").fill(" ")
            page.get_by_role("button", name="Next").click()

            # Check if this is still in markdown
            expect(page.get_by_test_id("NewTaskPage").locator('span')).to_have_count(1)
            expect(page.get_by_test_id("NewTaskPage").locator('span')).to_have_text(" ")

        finally:
            # Stop tracing and save it to a file
            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            # Clean the trace
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
