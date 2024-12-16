import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import imaplib
import email
from email.header import decode_header
import re
import time
from playwright.sync_api import sync_playwright, expect, Page

# Constants for the test
SITE_URL = "https://dev.new.expensify.com:8082/"
EMAIL = "totherandomuser+50357@gmail.com"
USER_PASSWORD = "umei djwi bfmp jntm"
BROWSER_WIDTH = 1280
BROWSER_HEIGHT = 720

# Function to fetch the magic sign-in code
def get_magic_code(email_address, password, retries=5, delay=5):
    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    imap.login(email_address, password)

    for _ in range(retries):
        imap.select("inbox")
        status, messages = imap.search(None, '(UNSEEN SUBJECT "Expensify magic sign-in code:")')
        if status == "OK":
            email_ids = messages[0].split()
            if email_ids:
                latest_email_id = email_ids[-1]
                _, msg_data = imap.fetch(latest_email_id, "(RFC822)")
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        subject, encoding = decode_header(msg["Subject"])[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding or "utf-8")
                        match = re.search(r"Expensify magic sign-in code: (\d+)", subject)
                        if match:
                            imap.logout()
                            return match.group(1)
        time.sleep(delay)

    imap.logout()
    return None

# Function to log in to Expensify
def login_to_expensify(page: Page, email_address: str, password: str):
    page.goto(SITE_URL)
    email_input = page.locator('input[type="email"]')
    expect(email_input).to_be_visible()
    email_input.fill(email_address)
    page.locator('button[role="button"]:has-text("Continue")').click()

    # otp = get_magic_code(email_address, password)
    otp = "123456"
    otp_input = page.locator('input[name="validateCode"]')
    expect(otp_input).to_be_visible()
    otp_input.fill(otp)

# Function to navigate and validate workspace settings
def navigate_to_workspace_settings(page: Page):
    settings_button = page.locator('button[aria-label="My settings"]')
    expect(settings_button).to_be_visible()
    settings_button.click()

    workspace_button = page.locator("div[aria-label='Workspaces']")
    expect(workspace_button).to_be_visible()
    workspace_button.click()

    workspace_item = page.locator("button").filter(has_text="John Doe's Workspace.default-")
    expect(workspace_item).to_be_visible()
    workspace_item.click()

# Function to enable accounting feature
def enable_accounting_feature(page: Page):
    accounting_button = page.locator("div[aria-label='Accounting']")
    expect(accounting_button).to_be_visible()
    accounting_button.click()

    three_dots_button = page.locator('button[aria-label="More"]').last
    expect(three_dots_button).to_be_visible()
    three_dots_button.click()

# Main test function
def test_expensify_50357():
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
        context = browser.new_context(viewport={"width":BROWSER_WIDTH,"height":BROWSER_HEIGHT})
        page = context.new_page()

        # Step 1: Log in to Expensify
        login_to_expensify(page, EMAIL, USER_PASSWORD)

        # Step 2: Navigate to workspace settings
        navigate_to_workspace_settings(page)

        # Step 3: Enable accounting feature
        enable_accounting_feature(page)

        # Test: Verify that Enter your credentials div shows up when authentication error occurs
        # First ensure the authentication error message is showing
        authentication_error = page.locator('span:has-text("Can’t connect to Quickbooks Online due to an authentication error.")')
        authentication_error.count() > 0, "Please setup authentication error through patch"

        # Now check Enter your credentials option is visible
        enter_credentials_div = page.locator('div:has-text("Enter your credentials")')
        enter_credentials_div_count = enter_credentials_div.count()
        assert enter_credentials_div_count > 0, "Enter your credentials option is not found"

        browser.close()
