import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
import imaplib
import email
from email.header import decode_header
import re
import time
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page
from enum import Enum

from utils.trace_cleaner import trace_cleaner

TEST_URL = "https://dev.new.expensify.com:8082"
USER_NAME = "testrecord49077"
USER_PASSWORD = ""


class TodayOptions(Enum):
    TRACK_AND_BUDGET_EXPENSES = 1
    SOMETHING_ELSE = 4


def get_test_user_info(seed=None):
    """
    Get test user info using the seed:
    - If `seed` is None, this function will return a fixed email and name.
    - If `seed` is the `True` boolean value, this function will generate a random number based on the current timestamp and use it as the seed to return a random email and name.
    - Otherwise, this function will return a derivative of the fixed email and corresponding name.
    """
    if seed is None:
        return {"email": f"{USER_NAME}@gmail.com", "password": USER_PASSWORD, "first_name": f"{USER_NAME}",
                "last_name": "Test"}

    if type(seed) == type(True):
        seed = int(time.time())

    return {"email": f"{USER_NAME}+{seed}@gmail.com", "password": USER_PASSWORD, "first_name": f"{USER_NAME}+{seed}",
            "last_name": "Test"}


def wait(page, for_seconds=2):
    page.wait_for_timeout(for_seconds * 1000)


def get_magic_code(user_email, password, page, retries=5, delay=10):
    # Connect to the server
    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    imap.login(user_email, password)
    for _ in range(retries):
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
        wait(page)

    imap.logout()
    print("Max retries reached. Email not found.")
    return None


def choose_what_to_do_today_if_any(page, option: TodayOptions, retries=5, **kwargs):
    wait(page)
    try:
        for _ in range(retries):
            wdyw = page.locator("text=What do you want to do today?")
            if wdyw.count() == 0:
                print('"What do you want to do today?" dialog is not found. Wait and retry...')
                wait(page)
            else:
                break
        if wdyw.count() == 0:
            print('"What do you want to do today?" dialog is not found.')
            set_full_name(page=page, first_name=kwargs['first_name'], last_name=kwargs['last_name'])
            return
        expect(wdyw).to_be_visible()
        if option == TodayOptions.SOMETHING_ELSE:
            text = "Something else"
        elif option == TodayOptions.TRACK_AND_BUDGET_EXPENSES:
            text = 'Track and budget expenses'
        page.locator(f"text='{text}'").click()
        page.get_by_role("button", name="Continue").click()
        # Enter first name, last name and click continue
        wait(page)
        page.locator('input[name="fname"]').fill(kwargs['first_name'])
        page.locator('input[name="lname"]').fill(kwargs['last_name'])
        wait(page)
        page.get_by_role("button", name="Continue").last.click()
        wait(page)
        if page.get_by_label("Close").count() > 0:
            page.get_by_label("Close").click()
    except:
        pass


def choose_link_if_any(page, link_text, retries=5):
    try:
        wait(page)
        for _ in range(retries):
            link = page.locator(f'text={link_text}')
            if link.count() == 0:
                print(f'"{link_text}" link is not found. Wait and retry...')
                wait(page)
            else:
                break
        if link.count() == 0:
            print(f'"{link_text}" link is not found.')
            return
        expect(link).to_be_visible()
        link.click()
    except Exception as e:
        print(e)
        return


def login(p: PlaywrightContextManager, user_info, if_phone=False) -> tuple[Browser, Page, str]:
    permissions = ['clipboard-read', 'clipboard-write']
    browser = p.chromium.launch(
        channel="chrome",
        headless=True,
        args=["--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"],
        proxy={"server": "http://localhost:8080"},
        slow_mo=500
    )
    if if_phone:
        phone = p.devices['iPhone 12 Pro']
        context = browser.new_context(**phone, permissions=permissions, reduced_motion='no-preference')
    else:
        context = browser.new_context()
    page = context.new_page()
    page.goto(TEST_URL, timeout=120000)
    phone_or_email_input = page.locator('input[type="email"]')
    expect(phone_or_email_input).to_be_visible()
    phone_or_email_input.fill(user_info["email"])
    continue_button = page.locator('button[tabindex="0"]')
    expect(continue_button).to_be_visible()
    continue_button.click()
    # Click Join button if the user is new. Or, use Magic Code to sign in if the user is existing.
    wait(page)
    join_button = page.locator('button:has-text("Join")')
    if join_button.count() > 0:
        print("Join button found. This is a new user.")
        join_button.click()
    else:
        print("Join button not found. This is an existing user. Use Magic Code to sign in.")
        magic_code = get_magic_code(user_info["email"], user_info["password"], page, retries=3, delay=10)
        print(f"Magic code: {magic_code}")

        validate_code_input = page.locator('input[data-testid="validateCode"]')
        expect(validate_code_input).to_be_visible()
        validate_code_input.fill(magic_code)
    return browser, page


def set_full_name(page, first_name, last_name):
    if page.get_by_label("Close").count() > 0:
        page.get_by_label("Close").click()
    page.get_by_label("My settings").click()
    page.get_by_role("menuitem", name="Profile").click()
    page.get_by_text("Display name").click()
    page.get_by_role("textbox", name="First name").click()
    page.get_by_role("textbox", name="First name").fill(first_name)
    page.get_by_role("textbox", name="Last name").click()
    page.get_by_role("textbox", name="Last name").fill(last_name)
    page.get_by_role("button", name="Save").click()
    wait(page)
    if page.get_by_label("Back").count() > 0:
        page.get_by_label("Back").last.click()
    page.get_by_label("Inbox").click()


def create_workspace_and_create_custom_report(page: Page):
    wait(page)
    page.get_by_label("My settings").click()
    page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").get_by_text("Workspaces").click()
    page.get_by_label("New workspace").first.click()
    page.get_by_text("More features").click()
    wait(page)
    # Enable Rules toggle
    if not page.get_by_label("Configure when receipts are").is_checked():
        page.get_by_label("Configure when receipts are").click()
        # Upgrade process
        page.get_by_role("button", name="Upgrade").click()
        wait(page)
        page.get_by_role("button", name="Got it, thanks").click()
        wait(page)
    # Enable Report fields and Rules
    page.locator('button[aria-label="Set up custom fields for spend."][role="switch"]').click()
    page.locator('div[aria-label="Rules"][role="menuitem"]').click()
    page.locator('button[aria-label="Custom report names"][role="switch"]').click()
    wait(page)
    # Set custom report name
    page.locator('div:has-text("Custom name")').last.click()
    name_input_field = page.locator('input[aria-label="Name"]')
    name_input_field.fill("")
    name_input_field.type("My WS Report")
    page.locator('button[role="button"]:has-text("Save")').click()
    wait(page)
    # Navigate back to Inbox
    page.locator('button[aria-label="Back"][role="button"]').last.click()
    page.locator('button[aria-label="Inbox"][role="button"]').click()
    wait(page)
    page.locator('button[aria-label="Navigates to a chat"]', has_text="'s Workspace").first.click()
    page.locator('button[aria-label="Create"]').last.click()
    wait(page)


def verify_custom_report_name_delete(page: Page) -> None:
    create_workspace_and_create_custom_report(page)
    page.locator('div[aria-label="Submit expense"]').click()
    page.locator('button[aria-label="Manual"][role="button"]').click()
    wait(page)

    # Fill in expense details
    page.locator('input[placeholder="0"]').fill("666")
    page.locator('button:has-text("Next")').first.click()
    page.locator('div:has-text("Merchant")').last.click()
    page.locator('input[aria-label="Merchant"]').last.fill("test")
    page.locator('button:has-text("Save")').click()
    page.locator('button:has-text("Submit")').last.click()
    wait(page)

    # View report details
    page.locator('button[aria-label="View details"][role="button"]').first.click()
    page.locator('div[aria-label="My WS Report"][role="menuitem"]').last.click()

    # Handle deletion
    three_dot_menu = page.locator('button[aria-label="More"][role="button"]').last

    if three_dot_menu.is_visible():
        three_dot_menu.click()
        page.locator('div:has-text("Delete")').last.click()
        page.locator('button:has-text("Delete")').first.click()

        # Ensure the report is deleted
        expect(page.locator('div[aria-label="My WS Report"][role="menuitem"]').last).not_to_be_visible()


def test_49077():
    with sync_playwright() as p:
        user_info = get_test_user_info(seed=12)
        browser, page = login(p, user_info, False)
        context = page.context

        # Start tracing
        context.tracing.start(snapshots=True, screenshots=True)
        try:
            # Step 2: Skip onboarding/start pages if any
            choose_what_to_do_today_if_any(page, TodayOptions.SOMETHING_ELSE, **user_info)
            # A new user will see this Get Started link on the first logon.
            choose_link_if_any(page, "Get started")
            # Possibly redirect to not-found page, so go back home.
            choose_link_if_any(page, "Go back to home page")

            verify_custom_report_name_delete(page)
            wait(page)
        except Exception as e:
            print(f"Test failed: {e}")
            raise
        finally:
            # Stop tracing and clean trace
            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            context.close()
            browser.close()
