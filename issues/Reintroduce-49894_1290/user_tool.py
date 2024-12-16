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

# Gmail credentials with app-specific password
user_email = "playwright2user+20@gmail.com"
password = "zehr mglm gizg gjcc"

# Function to fetch the verification link from Gmail
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

    input_code = page.locator('[autocomplete="one-time-code"]')
    input_code.fill("123456")

# Function to perform login using Playwright

def login_and_verify(p):
    # Browser permissions
    browser = p.chromium.launch(channel="chrome", headless=True, slow_mo=500, args=[
        "--disable-web-security",
        "--disable-features=IsolateOrigins,site-per-process"
    ])
    context = browser.new_context(ignore_https_errors=True)
    # Start tracing here
    context.tracing.start(screenshots=True, snapshots=True)
    page = context.new_page()

    # Go to login page
    page.goto('https://dev.new.expensify.com:8082/')

    login(page)

    try:
        continue_button = page.locator('button[tabindex="0"]')
        expect(continue_button).to_be_visible()
        continue_button.click()
    except Exception as e:
        pass

    # Click Create
    create_button = page.locator("[aria-label='Start chat (Floating action)']")
    create_button.click()
    page.wait_for_timeout(1)

    # Click Start Chat
    start_chat_button = page.locator("text=Start chat")
    start_chat_button.click()
    page.wait_for_timeout(1)

    # Click Room
    room_button = page.locator("[aria-label='Room']")
    room_button.click()
    page.wait_for_timeout(1)

    # Input Room Name
    page.locator('input[aria-label="Room name"]').fill(f'test name {int(time.time())}')

    # Input Room Description
    description_button = page.locator('[aria-label="Room description (optional)"]').nth(1)
    description_button.click()
    description_button.fill("`   `")
    page.wait_for_timeout(1)

    #  Click Create Room
    create_room_button = page.locator('text=Create room')
    create_room_button.click()
    page.wait_for_timeout(1)

    # Click Create second button
    create2_button = page.locator("[aria-label='Create']").nth(1)
    create2_button.click()
    page.wait_for_timeout(1)

    # Click Assign Task
    assign_task_button = page.locator('text=Assign task')
    assign_task_button.click()
    page.wait_for_timeout(1)

    # Input Title
    page.locator('input[aria-label="Title"]').fill('test')

    # Input Description
    description2_button = page.locator('[aria-label="Description (optional)"]').nth(1)
    description2_button.click()
    description2_button.fill("`   `")
    page.wait_for_timeout(1)

    # Click Next
    next_button = page.locator("text=Next")
    next_button.click()
    page.wait_for_timeout(1)

    # Input Space in Description
    description3_button = page.locator('[aria-label="`   `"]')
    description3_button.click()
    page.keyboard.press(" ")
    page.wait_for_timeout(1)

    # Click Next
    next2_button = page.locator("text=Next").nth(1)
    next2_button.click()
    page.wait_for_timeout(1)

    # Check if markdown box exists
    markdown_box = page.locator('text=Description').nth(1)
    markdown_box.click()
    input_field = page.locator('[aria-label="Description (optional)"]').nth(3)
    expect(input_field).to_contain_text("`   `")
    page.wait_for_timeout(1)

    return browser, page, context

# Main test function

def test():
    with sync_playwright() as p:
        browser, page, context = None, None, None
        try:
            browser, page, context = login_and_verify(p)
            # Any test wait or extra steps can go here
            if page:
                page.wait_for_timeout(5000)
        except Exception as e:
            print(f"Test failed: {e}")
        finally:
            if context:
                context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
                trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            if browser:
                browser.close()