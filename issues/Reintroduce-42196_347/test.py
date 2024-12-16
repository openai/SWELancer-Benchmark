import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
from playwright.sync_api import sync_playwright, expect, Page
import os
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


URL = "https://dev.new.expensify.com:8082/"
platform = "desktop"
browser_type = "chromium"


def generate_email(user_name="expensify66", domain="gmail.com"):
    """
    Generate an email with a timestamp
    """
    timestamp = int(time.time())
    return f"{user_name}+{timestamp}@{domain}"


def launch_browser(
    playwright
):
    browser = playwright.chromium.launch(headless=True, args=[
        "--disable-web-security",
        "--disable-features=IsolateOrigins,site-per-process",
        "--ignore-certificate-errors"
    ])
    page = browser.new_page()

    return browser, page


def login_user_if_not_logged_in(
    page: Page, data_dir: str, first_name="Asaad", last_name="I", platform="desktop"
):
    # Launch chromiun and open ne   w page
    page.bring_to_front()

    # Step 1: Open expensify url
    page.goto(URL)

    page.get_by_test_id("username").fill(EMAIL_USERNAME)
    page.get_by_role("button", name="Continue").click()
    # Check if OTP is required for the login
    try:
        expect(page.get_by_test_id("SignInPage").get_by_test_id("validateCode")).to_be_visible(timeout=5000)
    except (AssertionError, TimeoutError):
        # If not required, expect the join button to appear and click the button
        page.get_by_test_id("SignInPage").get_by_role("button", name="Join").click()
    else:
        # Get the OTP and complete verification
        otp_code = "123456"# get_magic_code(EMAIL_USERNAME, EMAIL_PASSWORD)
        page.get_by_test_id("SignInPage").get_by_test_id("validateCode").fill(otp_code)
        # try:
        #     page.get_by_test_id("SignInPage").get_by_role("button", name="Sign in").click(timeout=2000)
        # except (AssertionError, TimeoutError):
        #     pass

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


def test_manual_expense_description_cursor_should_not_overlap_with_text_content():
    with sync_playwright() as p:
        # Login user
        browser, page = launch_browser(p)

        first_name = "User"
        last_name = "One"

        # Email of the first logged in user.
        login_user_if_not_logged_in(page, first_name, last_name)

        random_email = generate_email()

        # Submit a new expense
        page.get_by_label("Start chat (Floating action)").click()

        submit_expense_button = page.get_by_role("menuitem", name="Submit expense")
        submit_expense_button.click()

        # click Manual expense option
        manual_expense_button = page.get_by_role("button", name="Manual")
        manual_expense_button.click()

        # Enter expense amount
        page.get_by_placeholder("0").fill("100")
        page.locator("#numPadContainerView").get_by_role("button", name="Next").click()

        # Search user 1 to submit expense to.
        page.get_by_test_id("selection-list-text-input").click()
        page.get_by_test_id("selection-list-text-input").fill(random_email)
        page.get_by_label(random_email).click()

        # Enter description.
        page.get_by_role("menuitem", name="Description").click()
        page.get_by_role("textbox", name="What's it for?").type("> hey")

        # Verification step: Check to see if padding right is any non-zero value.
        blockquote_element = page.locator('span[data-type="blockquote"]')
        expect(blockquote_element).to_have_css("padding-right", "1px")

        browser.close()

