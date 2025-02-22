"""
Test to verify that the row's selected style should have the rounded edges
"""
import time
import os
import re
import email
import email.utils
import imaplib
from email.header import decode_header
import platform
from playwright.sync_api import sync_playwright, Page
import pytest
import numpy as np
from PIL import Image

# Global Variables
USER_DATA_DIR = os.path.join(os.getcwd(), "browser_data_52158")
PERSISTENT = False
GMAIL_USER_NAME = "testemail.ameen"
NOW = int(time.time())
USER_EMAIL = f"{GMAIL_USER_NAME}+52158@gmail.com"
PASSWORD = "yjsp jfez uvmy gkgs"
URL = "https://dev.new.expensify.com:8082/"

def get_magic_code(
    page: Page, user_email: str, password: str, current_timestamp: int, retries=5
):
    """
    Retrieves the Expensify magic sign-in code from the user's email inbox.

    Args:
        page (Page): The page object to control browser actions.
        user_email (str): The email address to log in to the IMAP server.
        password (str): The password for the email address.
        current_timestamp (int): The current timestamp to filter out old emails.
        retries (int, optional): The number of attempts to check for the email. Defaults to 5.
        delay (int, optional): The delay in milliseconds between retries. Defaults to 10000.

    Returns:
        str: The magic sign-in code if found, otherwise None.
    """
    delay=10000
    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    imap.login(user_email, password)
    page.wait_for_timeout(delay)

    for attempt in range(retries):
        print(f"Attempt {attempt}")

        if attempt > 0:
            print(f"Waiting {delay} milliseconds before next attempt...")
            page.wait_for_timeout(delay)

        imap.select("inbox")
        status, messages = imap.search(
            None, '(UNSEEN SUBJECT "Expensify magic sign-in code:")'
        )

        if status != "OK" or not messages[0]:
            continue

        latest_email_id = messages[0].split()[-1]
        status, msg_data = imap.fetch(latest_email_id, "(RFC822)")

        if status != "OK":
            continue

        for response_part in msg_data:
            msg = email.message_from_bytes(response_part[1])
            email_date = msg.get("Date")
            email_timestamp = email.utils.mktime_tz(
                email.utils.parsedate_tz(email_date)
            )

            if email_timestamp < current_timestamp:
                print(f"Found old email from {email_date}, waiting for new one...")
                break

            imap.store(latest_email_id, "+FLAGS", "\\Seen")
            subject, encoding = decode_header(msg["Subject"])[0]
            subject = subject.decode(encoding or "utf-8") if isinstance(subject, bytes) else subject

            match = re.search(r"Expensify magic sign-in code: (\d+)", subject)
            if match:
                code = match.group(1)
                imap.logout()
                return code

    imap.logout()
    print("Max retries reached. Email not found.")
    return None

def login(page: Page, user_email: str, first_name: str = "Test", last_name: str = "User"):
    """
    Logs into the Expensify application using the provided user email.

    Args:
        page (Page): The Playwright page object to interact with the browser.
        user_email (str): The email address of the user to log in.
        first_name (str, optional): The first name of the user. Defaults to "Test".
        last_name (str, optional): The last name of the user. Defaults to "User".

    Raises:
        Exception: If any step fails or an expected element is not found.
    """

    # Step 1: Open expensify url
    page.goto(URL)

    if page.locator('input[type="email"]').is_visible():
        # Step 2: Enter email and click continue
        page.locator('input[type="email"]').fill(user_email)
        page.locator('button[tabindex="0"]').click()
        page.wait_for_timeout(2000)

        if page.locator("text=Please enter the magic code sent to").is_visible():
            # Handle OTP
            expensify_otp = "123456" #get_magic_code(page, USER_EMAIL, PASSWORD, NOW)
            page.fill('input[inputmode="numeric"]', expensify_otp)
            page.wait_for_load_state("load")
        else:
            page.locator('button[tabindex="0"]').click()
        page.wait_for_load_state("load")

    page.wait_for_timeout(2000)
    onboarding_screen = page.locator("text=What do you want to do today?")
    if onboarding_screen.is_visible():
        page.locator("text='Get paid back by my employer'").click()
        page.get_by_role("button", name="Continue").click()
        page.locator('input[name="fname"]').wait_for(
            state="visible", timeout=10000
        )

        # Step 4: Enter first name, last name and click continue
        page.locator('input[name="fname"]').fill(first_name)
        page.locator('input[name="lname"]').fill(last_name)
        page.get_by_role("button", name="Continue").last.click()

def setup_browser(p, data_dir):
    """
    Set up and launch a Chromium browser instance.

    Args:
        p (playwright.sync_api.Playwright): The Playwright instance used to launch the browser.

    Returns:
        tuple: A tuple containing the browser instance and the page instance.
    """
    launch_args = {
        "headless": False,
        "slow_mo": 500,
        "proxy": {"server": "http://localhost:8080"},
        "args": ["--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"],
    }

    if PERSISTENT:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=data_dir,
            **launch_args
        )
        page = browser.pages[0] if browser.pages else browser.new_page()
        context = browser
    else:
        browser = p.chromium.launch(**launch_args)
        context = browser.new_context()
        page = context.new_page()

    return browser, context, page

def create_workspace(page: Page):
    """
    Creates a new workspace using the given page object add added the members.

    Args:
        page (Page): The page object representing the current browser page.
    """
    page.get_by_label("Start chat (Floating action)").click()
    if page.get_by_label("New workspace").is_visible():
        page.get_by_label("New workspace").click()
    else:
        page.locator('button[aria-label="My settings"]').click()
        page.get_by_test_id("InitialSettingsPage").locator('div[aria-label="Workspaces"]').click()
        page.get_by_label("row").nth(0).click()

def invite_members(page: Page):
    """
    Invites a member to the workspace using the provided page object.

    Args:
        page: The page object representing the current state of the application.
    """
    page.get_by_text("Members").click()
    page.get_by_role("button", name="Invite member").click()
    page.get_by_test_id("selection-list-text-input").fill(MEMBER_EMAIL)
    page.wait_for_timeout(1000)
    page.keyboard.press("Tab")
    page.keyboard.press("Enter")
    page.locator('button').filter(has_text="Next").click()
    page.locator('button[data-listener="Enter"]').filter(has_text="Invite").click()

def test_row_selected_style_rounded_edge():
    """
    Test to verify that the row's selected style should have the rounded edges
    """
    with sync_playwright() as p:
        # Step 1: Login user and complete the onboarding
        browser, context, page = setup_browser(p, USER_DATA_DIR)
        login(page, USER_EMAIL)

        try:
            # Step 2: Press the shortcut to open a search dialog
            if platform.system() == "Darwin":  # macOS
                page.keyboard.press("Meta+K")  # ⌘ + K
            else:
                page.keyboard.press("Control+K")  # Ctrl + K

            # Step 3: Press ArrowDown key 2 times
            page.keyboard.press("ArrowDown")  # First press
            page.keyboard.press("ArrowDown")  # Second press

            # Step 4: Capture element screenshot
            selected_row = page.get_by_test_id("selection-list").get_by_label("Concierge", exact=True).first
            screenshot_path = "highlighted_corner_check.png"
            selected_row.screenshot(path=screenshot_path)  # Capture screenshot

            # Step 5: Load image and check pixel colors
            img = Image.open(screenshot_path)
            pixels = np.array(img)

            # Check corner pixels for transparency or background color (rounded corners)
            top_left = pixels[2, 2]
            top_right = pixels[2, -3]
            bottom_left = pixels[-3, 2]
            bottom_right = pixels[-3, -3]

            # Step 6: Validate highlighted color and rounded effect
            highlight_color = [242, 237, 231]  # highlight color
            assert not np.array_equal(top_left, highlight_color), "Top-left corner not rounded"
            assert not np.array_equal(top_right, highlight_color), "Top-right corner not rounded"
            assert not np.array_equal(bottom_left, highlight_color), "Bottom-left corner not rounded"
            assert not np.array_equal(bottom_right, highlight_color), "Bottom-right corner not rounded"

            # Close the browser
            browser.close()

        except Exception as e:
            pytest.fail(f'{e}')
