"""
Test to verify that the adding animation for children of switch components.
"""
import time
import os
import re
import email
import email.utils
import imaplib
from email.header import decode_header
from playwright.sync_api import sync_playwright, Page
import pytest

# Global Variables
USER_DATA_DIR = os.path.join(os.getcwd(), "browser_data_53759")
PERSISTENT = False
GMAIL_USER_NAME = "testemail.ameen"
NOW = int(time.time())
USER_EMAIL = f"{GMAIL_USER_NAME}+53759@gmail.com"
MEMBER_EMAIL = "testuser@gmail.com"
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

    # Open expensify url
    page.goto(URL)
    try:
        page.get_by_test_id("username").wait_for(state="visible", timeout=10000)
    except Exception:
        pass
    if page.get_by_test_id("username").is_visible():
        # Enter email and click continue
        page.get_by_test_id("username").fill(user_email)
        page.locator('button[tabindex="0"]').click()
        page.wait_for_timeout(2000)
        if page.locator("text=Please enter the magic code sent to").is_visible():
            # Handle OTP
            expensify_otp = '123456' #get_magic_code(page, USER_EMAIL, PASSWORD, NOW)
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

        # Enter first name, last name and click continue
        page.locator('input[name="fname"]').fill(first_name)
        page.locator('input[name="lname"]').fill(last_name)
        page.get_by_role("button", name="Continue").last.click()

def setup_browser(p, data_dir):
    """
    Set up and launch a Chromium browser instance.

    Args:
        p (playwright.sync_api.Playwright): The Playwright instance used to launch the browser.
        data_dir (str): The directory to store browser data.

    Returns:
        tuple: A tuple containing the browser instance, context, and the page instance.
    """
    launch_args = {
        "headless": False,
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
    Navigates through the given page to create or access a workspace.

    Args:
        page (Page): The page object representing the current web page.
    """
    page.locator('button[aria-label="Start chat (Floating action)"]').click()
    if page.get_by_label("New workspace").is_visible():
        page.get_by_label("New workspace").click()
    else:
        page.get_by_label("My settings").click()
        page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()
        page.get_by_label("row").nth(0).click()  # Click on Workspace

def test_adding_animation_for_switch_component_children():
    """
    Test to verify that the adding animation for children of switch components.
    """
    with sync_playwright() as p:
        # Step 1: Login user and complete the onboarding
        browser, context, page = setup_browser(p, USER_DATA_DIR)
        login(page, USER_EMAIL)

        try:
            # Step 2: Navigate to workspace
            create_workspace(page)

            # Step 3: Navigate to More features page and enable required features
            if not page.get_by_label("Workflows").is_visible():
                page.get_by_label("More features").click()
                # Workflow to add manual approval
                if not page.get_by_label("Configure how spend is").is_checked():
                    page.get_by_label("Configure how spend is").click()
            # Step 4: Click workflow
            page.get_by_label("Workflows").click()
            page.wait_for_timeout(1000)

            # Step 5: Click to enable additional approval
            if page.get_by_label("Require additional approval").is_checked():
                page.get_by_label("Require additional approval").click()

            page.wait_for_timeout(1000)
            page.get_by_label("Require additional approval").click()

            # Step 6: Locate the element that contains the approval settings
            locator = page.get_by_label("Add approvals").locator("xpath=ancestor::*[10]")
            if locator.locator("text=Delay submissions").is_visible():
                locator = page.get_by_label("Add approvals").locator("xpath=ancestor::*[8]")

            # Step 7: Loop to check the animation properties
            for _ in range(2):
                # Get the height of the element
                style = locator.evaluate("el => window.getComputedStyle(el)")
                height = float(style["height"].replace("px", ""))
                page.wait_for_timeout(20)  # Adjust timing based on animation speed

                # Step 8: Assert that the height is within the expected range during animation
                assert 0 < (height) < 366, f"Height value {height} is invalid. Expected between 0 and 366."

            # Close the browser
            browser.close()

        except Exception as e:
            pytest.fail(f'{e}')
