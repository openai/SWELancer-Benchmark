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

# Function to fetch the magic code from email
def get_magic_code(user_email, password, since=None, retries=5, delay=10):
    # Step 1: Initialize email fetching parameters
    if since is None:
        since = datetime.now(timezone.utc).replace(second=0, microsecond=0)

    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    
    # Step 2: Login to the email account
    imap.login(user_email, password)

    for _ in range(retries):
        # Step 3: Select the inbox and search for unread magic code emails
        imap.select("inbox")
        status, messages = imap.search(None, '(UNSEEN SUBJECT "Expensify magic sign-in code:")')

        if status == "OK":
            email_ids = messages[0].split()

            if email_ids:
                # Step 4: Fetch the latest email
                latest_email_id = email_ids[-1]
                status, msg_data = imap.fetch(latest_email_id, "(RFC822)")

                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        # Step 5: Parse email content and look for the magic code
                        msg = email.message_from_bytes(response_part[1])
                        subject, encoding = decode_header(msg["Subject"])[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding or "utf-8")

                        match = re.search(r"Expensify magic sign-in code: (\d+)", subject)
                        email_date = email.utils.parsedate_to_datetime(msg["Date"])
                        if match and email_date >= since:
                            # Step 6: Return the extracted magic code
                            code = match.group(1)
                            imap.logout()
                            return code
                print("Email doesn't match conditions. Retrying...")
            else:
                print("No unread emails found with the subject. Retrying...")
        else:
            print("Failed to retrieve emails. Retrying...")
        time.sleep(delay)

    # Step 7: Logout from IMAP and return None after max retries
    imap.logout()
    print("Max retries reached. Email not found.")
    return None


def login_user(p: PlaywrightContextManager, first_name="Milan", last_name="T") -> tuple[Browser, Page, str]:
    # Launch chromiun and open new page
    browser = p.chromium.launch(headless=True, args=[
        "--disable-web-security",
        "--disable-features=IsolateOrigins,site-per-process",
        "--ignore-certificate-errors"
    ])
    page = browser.new_page()
    user_email = EMAIL_USERNAME

    # Step 1: Open expensify url
    page.goto('https://dev.new.expensify.com:8082/') 

    # Step 2: Enter email and click continue
    page.get_by_test_id("username").fill(user_email)
    page.get_by_role("button", name="Continue").click()
    # Check if OTP is required for the login
    try:
        expect(page.get_by_test_id("SignInPage").get_by_test_id("validateCode")).to_be_visible(timeout=5000)
    except (AssertionError, TimeoutError):
        # If not required, expect the join button to appear and click the button
        page.get_by_test_id("SignInPage").get_by_role("button", name="Join").click()
    else:
        # Get the OTP and complete verification
        otp_code = "123456" #get_magic_code(EMAIL_USERNAME, EMAIL_PASSWORD)
        otp_input = page.locator('input[autocomplete="one-time-code"]')
        otp_input.fill(otp_code)

    # Check if onboarding is required
    try:
        expect(page.get_by_text("What do you want to do today?")).to_be_visible(timeout=5000)
    except (AssertionError, TimeoutError):
        pass
    else:
        # Complete the onboarding
        page.get_by_label("Track and budget expenses").click()
        page.get_by_role("textbox", name="First name").fill(first_name)
        page.get_by_role("textbox", name="Last name").fill(last_name)
        page.get_by_role("button", name="Continue").click()

    return browser, page, user_email


def test_edit_box_and_compose_box_alignment():
    with sync_playwright() as p:
        browser, page, user_email = login_user(p)
        context = page.context

        # Start tracing
        context.tracing.start(screenshots=True, snapshots=True)

        try:
            # Step 2: Open personal chat
            personal_chat = page.get_by_text(f"Milan T (you)").first
            expect(personal_chat).to_be_visible()
            personal_chat.click()

            # Step 3: Send a message
            message_one = page.get_by_role("textbox").fill("My Message")
            page.get_by_role("textbox").press("Enter")
            page.wait_for_timeout(500)

            # Step 4: Right click on the message, and option menu should be visible
            message_two = page.get_by_role("textbox").fill("My Second Message")
            page.get_by_role("textbox").press("Enter")
            page.wait_for_timeout(500)

            # Step 4: Right click on the message, and option menu should be visible
            message_three = page.get_by_role("textbox").fill("My Third Message")
            page.get_by_role("textbox").press("Enter")
            page.wait_for_timeout(500)

            message_three = page.locator('span', has_text="My Third Message")
            message_three.click(button="right")

            option_menu = page.locator('div[aria-label="Edit comment"]', has_text="Edit comment")
            option_menu.click()
            page.wait_for_timeout(2000)

            # Select the elements (replace with the actual selectors)
            element1 = page.locator("button[aria-label='Close']")
            element2 = page.locator("button[aria-label='Create']").nth(1)

            # Get the x-coordinates of the elements
            element1_x = element1.bounding_box()["x"]
            element2_x = element2.bounding_box()["x"]

            # Assert that they have the same x-coordinate, meaning they are vertically aligned
            assert element1_x == element2_x, f"Elements are not vertically aligned. Element1 x: {element1_x}, Element2 x: {element2_x}"
        finally:
            # Stop tracing and clean trace
            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            context.tracing.stop(path=trace_path)
            from utils.trace_cleaner import trace_cleaner
            trace_cleaner(trace_path)
            browser.close()
