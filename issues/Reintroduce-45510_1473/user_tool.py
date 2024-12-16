import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
import imaplib
import email
import random
from email.header import decode_header
import re
import time
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page
from enum import Enum

from utils.trace_cleaner import trace_cleaner

#### CONFIG

TEST_URL = "https://dev.new.expensify.com:8082/"
USER_NAME = "testuserexpensify1"
USER_PASSWORD = "aedyeaocujbrrcal"


#### UTILS

class TodayOptions(Enum):
    TRACK_AND_BUDGET_EXPENSES = 1
    SOMETHING_ELSE = 4

def get_test_user_info(seed = None):
    """
    Get test user info using the seed:
    - If `seed` is None, this function will return a fixed email and name.
    - If `seed` is the `True` boolean value, this function will generate a random number based on the current timestamp and use it as the seed to return a random email and name.
    - Otherwise, this function will return a derivative of the fixed email and corresponding name.
    """
    if seed is None:
        return {"email": f"{USER_NAME}@gmail.com", "password": USER_PASSWORD, "first_name": "Pratik", "last_name": "Test"}
    
    if type(seed) == type(True):
        seed = int(time.time())

    return {"email": f"{USER_NAME}+{seed}@gmail.com", "password": USER_PASSWORD, "first_name": f"Pratik+{seed}", "last_name": "Test"}

def wait(page, for_seconds=1):
    page.wait_for_timeout(for_seconds * 1000)

def get_magic_code(user_email, password, retries=2, delay=3):
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
                # if no match, continue
            else:
                pass
        else:
            pass

        # Wait for the specified delay before trying again
        time.sleep(delay)

    imap.logout()
    # print("Max retries reached. Email not found.")
    return "123456" # Default OTP

def choose_what_to_do_today_if_any(page, option: TodayOptions, retries = 1, **kwargs):
    wait(page)

    for _ in range(retries):
        wdyw = page.locator("text=What do you want to do today?")
        if wdyw.count() == 0:
            # print('"What do you want to do today?" dialog is not found. Wait and retry...')
            wait(page)
        else:
            break

    if wdyw.count() == 0:
        # print('"What do you want to do today?" dialog is not found.')
        return
        
    if option == TodayOptions.SOMETHING_ELSE:
        text = "Something else"
    elif option == TodayOptions.TRACK_AND_BUDGET_EXPENSES:
        text='Track and budget expenses'

    page.locator(f"text='{text}'").click()
    page.get_by_role("button", name="Continue").click()

    # Enter first name, last name and click continue
    wait(page)
    page.locator('input[name="fname"]').fill(kwargs['first_name'])
    page.locator('input[name="lname"]').fill(kwargs['last_name'])
    page.get_by_role("button", name="Continue").last.click()

def choose_link_if_any(page, link_text, retries = 3):
    wait(page)

    for _ in range(retries):
        link = page.locator(f'text={link_text}')
        if link.count() == 0:
            # print(f'"{link_text}" link is not found. Wait and retry...')
            wait(page)
        else:
            break

    if link.count() == 0:
        # print(f'"{link_text}" link is not found.')
        return 
    
    link.click()

def login(p: PlaywrightContextManager, user_info, if_phone=False) -> tuple[Browser, Page, object]:
    # Step 1: Input email and click Continue
    permissions = ['clipboard-read', 'clipboard-write']
    browser = p.chromium.launch(headless=True, args=["--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"])

    if if_phone:
        phone = p.devices['iPhone 12 Pro']
        context = browser.new_context(**phone, permissions=permissions, reduced_motion='no-preference')
    else:
        context = browser.new_context()

    # Start tracing right after context is created
    context.tracing.start(screenshots=True, snapshots=True, sources=True)

    page = context.new_page()

    page.goto(TEST_URL, timeout=20000)

    phone_or_email_input = page.locator('input[type="email"]')
    phone_or_email_input.fill(user_info["email"])

    continue_button = page.locator('button[tabindex="0"]')
    continue_button.click()

    # Step 2: Click Join button if the user is new. Or, use Magic Code to sign in if the user is existing.
    wait(page)

    join_button = page.locator('button:has-text("Join")')
    if join_button.count() > 0:
        # print("Join button found. This is a new user.")
        join_button.click()
    else:
        # print("Join button not found. This is an existing user. Use Magic Code to sign in.")
        magic_code = get_magic_code(user_info["email"], user_info["password"], retries=2, delay=3)
        print(f"Magic code: {magic_code}")

        validate_code_input = page.locator('input[data-testid="validateCode"]')
        validate_code_input.fill(magic_code)

    return browser, page, context


#### TESTS

def createWorkspace(page):
    settingsButton = page.locator('button[aria-label="My settings"]')
    settingsButton.click()
    wait(page)

    workspacesOption = page.locator('div[aria-label="Workspaces"]')
    workspacesOption.click()
    wait(page)

    newWsButton = page.locator('button[aria-label="New workspace"]').last
    newWsButton.click()
    wait(page)

def inviteMembers(page, email):
    membersOption = page.locator('div[aria-label="Members"]').last
    membersOption.click()
    wait(page)
    
    inviteMemberButton = page.get_by_role("button", name="Invite member").last
    inviteMemberButton.click()
    wait(page)

    memberField = page.get_by_test_id("selection-list-text-input")
    memberField.fill(email)
    memberField.press("Enter")
    wait(page,2)


    nextButton = page.get_by_role("button", name="Next").last
    nextButton.click()
    wait(page)

    inviteButton = page.get_by_role("button", name="Invite").last
    inviteButton.click()
    wait(page)

def removeMember(page):
    # selectMember = page.get_by_role("button", name=email)
    selectMember = page.get_by_role("button", name= "Pratik Babhulkar").first
    selectMember.click()
    wait(page)

    removeFromWs = page.get_by_role("button", name="Remove from workspace").last
    removeFromWs.click()
    wait(page)

def test():
    with sync_playwright() as p:
        user_info = get_test_user_info(seed=5)  # Use any seed that you like
        browser, page, context = login(p, user_info, False)
        trace_path = "/app/expensify/user_tool/output_browser1.zip"
        try:
            # Step 2: Skip onboarding/start pages if any
            choose_what_to_do_today_if_any(page, TodayOptions.SOMETHING_ELSE, **user_info)

            # Step 3: Follow instructions from the issue
            email = "praditik@gmail.com"
            createWorkspace(page)
            inviteMembers(page, email)
            removeMember(page)

            # Step 4: Assert the expected behavior
            msg = page.locator("text=is an approver in this workspace")
            expect(msg).not_to_be_visible()

        except Exception as e:
            # Re-raise to fail the test, but still ensure the trace is saved
            raise e
        finally:
            # Stop tracing and clean the trace
            context.tracing.stop(path=trace_path)
            trace_cleaner(trace_path)
            browser.close()
