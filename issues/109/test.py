"""
Test to verify that a placeholder thumbnail is added to expenses without a receipt.
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
USER_DATA_DIR = os.path.join(os.getcwd(), "browser_data_52638")
PERSISTENT = False
GMAIL_USER_NAME = "testemail.ameen"
NOW = int(time.time())
USER_EMAIL = f"{GMAIL_USER_NAME}+52638@gmail.com"
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

    # Step 1: Open expensify url
    page.goto(URL)

    if page.locator('input[type="email"]').is_visible():
        # Step 2: Enter email and click continue
        page.locator('input[type="email"]').fill(user_email)
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
        "slow_mo": 1000,
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
        page.get_by_role("button", name="Back").click()
        page.get_by_label("Inbox").click()
    else:
        page.keyboard.press("Escape")

def submit_expense_to_workspace(
    page: Page, amount: str = "10", merchant: str = "example.com"
):
    """
    Submits an expense to a workspace using the provided page object.

    Args:
        page (Page): The Playwright page object to interact with the web elements.
        amount (str, optional): The amount to be entered for the expense. Defaults to "10".
        merchant (str, optional): The merchant to be entered for the expense. Defaults to "example.com".

    Returns:
        None
    """

    # Click on + icon
    page.locator('button[aria-label="Start chat (Floating action)"]').click()

    if page.get_by_label("New workspace").is_visible():
        # Click on click expense
        page.get_by_label("Create expense").first.click()
        # Click on "Manual" button and enter amount
        page.locator('button[aria-label="Manual"]').click()
        # Enter amount
        page.locator('input[role="presentation"]').fill(amount)
        # Click on Next button
        page.locator('button[data-listener="Enter"]', has_text="Next").first.click()
        page.wait_for_timeout(1000)
        # Select workspace
        page.locator(
            'button[aria-label="Test User\'s Workspace"][tabindex="0"]'
        ).last.click()
        # Click on merchant
        page.locator('div[role="menuitem"]', has_text="Merchant").click()
        page.locator('input[aria-label="Merchant"]').fill(merchant)
        # Save the merchant
        page.locator('button[data-listener="Enter"]', has_text="Save").click()
        # Submit the expense
        page.locator('button[data-listener="Enter"]', has_text="Submit").click()
    else:
        page.keyboard.press("Escape")
        # Click on workspace chat
        page.get_by_test_id("lhn-options-list").locator('button[aria-label="Navigates to a chat"]:has-text("Test User\'s Workspace")').click()

def submit_expense_to_member(page):
    """
    Submits an expense to a member on the given page.

    Args:
        page (Page): The page object representing the current browser page.
    """
    if not page.get_by_test_id("lhn-options-list").locator('button[aria-label="Navigates to a chat"]:has-text("testuser somasundar")').is_visible():
        page.locator('button[aria-label="Start chat (Floating action)"]').click()
        page.get_by_label("Start chat", exact=True).first.click()
        page.locator('input[aria-label="Name, email, or phone number"]').fill("testuser@gmail.com")
        page.keyboard.press("Tab")
        page.keyboard.press("Tab")
        page.keyboard.press("Enter")
        page.get_by_role("button", name="Next").click()
        page.get_by_role("button", name="Start group").click()
        page.get_by_test_id("lhn-options-list").locator('button[aria-label="Navigates to a chat"]:has-text("Test, testuser")').click()
        page.locator('button[aria-label="Start chat (Floating action)"]').click()
        page.get_by_label("Create expense").first.click()

        if not page.get_by_role("button", name="View details").is_visible():
            page.get_by_label("Manual").click()
            page.get_by_placeholder("0").fill("20")
            page.locator("#numPadContainerView").get_by_role("button", name="Next").click()
            page.get_by_test_id("selection-list-text-input").fill("testuser@gmail.com")
            page.keyboard.press("Tab")
            page.keyboard.press("Enter")

            page.get_by_role("button", name="Submit ").click()
    page.get_by_test_id("lhn-options-list").locator('button[aria-label="Navigates to a chat"]:has-text("testuser somasundar")').click()

def test_expense_without_receipt_has_placeholder_thumbnail():
    """
    Test to verify that a placeholder thumbnail is added to expenses without a receipt.
    """
    with sync_playwright() as p:
        # Step 1: Login user and complete the onboarding
        browser, context, page = setup_browser(p, USER_DATA_DIR)
        login(page, USER_EMAIL)

        # Step 2: Create Workspace
        create_workspace(page)

        # Step 3: Submit expense into the workspace chat
        submit_expense_to_workspace(page)
        try:
            # Step 4: Verify that the placeholder thumbnail SVG is visible
            svg_elements = page.get_by_label("View details").get_by_label("Upload receipt").nth(1).locator("svg")
            page.wait_for_timeout(1500)

            if not svg_elements.count():
                pytest.fail("No placeholder thumbnail SVG found.")

            # Step 5: Click on expense to view
            svg_elements.click()
            page.wait_for_timeout(1200)

            # Step 6: Verify that the “add receipt placeholder” on the expense view to more closely matches the thumbnail presented on the preview.
            element = page.get_by_label("Upload receipt").nth(2).locator("path").nth(1)
            if not element.is_visible():
                element = page.get_by_label("Upload receipt").nth(1).locator("path").nth(1)
            if not element.is_visible():
                element = page.get_by_label("Upload receipt").nth(0).locator("path").nth(1)

            svg_content = element.evaluate("el => el.outerHTML")
            expected_svg = '<path d="M0 14C0 6.268 6.268 0 14 0s14 6.268 14 14-6.268 14-14 14S0 21.732 0 14Z" style="fill: rgb(3, 212, 124);"></path>'
            assert expected_svg == svg_content.strip(), f"SVG content mismatch:\n{svg_content}"

            # Step 7: Submit expense to a member
            submit_expense_to_member(page)

            # Step 8: Verify that the placeholder thumbnail SVG is visible
            svg_elements_member = page.get_by_label("View details").locator("svg")
            if not svg_elements_member.count():
                pytest.fail("No placeholder thumbnail SVG found.")

            # Step 9: Verify that the “add receipt placeholder” on the expense view to more closely matches the thumbnail presented on the preview.
            page.get_by_label("View details").nth(1).click()
            receipt_element = page.get_by_label("Upload receipt").nth(2).locator("path").nth(1)
            receipt_svg = receipt_element.evaluate("el => el.outerHTML")
            assert expected_svg == receipt_svg.strip(), f"SVG content mismatch:\n{receipt_svg}"

            # Close the browser
            browser.close()
        except Exception as e:
            pytest.fail(f'{e}')
