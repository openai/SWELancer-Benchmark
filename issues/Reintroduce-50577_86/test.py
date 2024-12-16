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

def get_magic_code(user_email, password, retries=5, delay=10):
    # Connect to the server
    return '123456'
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
                pass
        else:
            pass

        # Wait for the specified delay before trying again
        time.sleep(delay)

    imap.logout()
    return None

def choose_what_to_do_today_if_any(page, option: TodayOptions, retries = 3, **kwargs):
    wait(page)

    for _ in range(retries):
        wdyw = page.locator("text=What do you want to do today?")
        if wdyw.count() == 0:
            wait(page)
        else:
            break

    if wdyw.count() == 0:
        return 
    
    expect(wdyw).to_be_visible()
        
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


def login(p: PlaywrightContextManager, user_info, if_phone=False) -> tuple[Browser, Page, object]:    
    # Step 1: Input email and click Continue
    permissions = ['clipboard-read', 'clipboard-write']
    browser = p.chromium.launch(headless=True, args = [
        "--disable-web-security",
        "--disable-features=IsolateOrigins, site-per-process"
        ], slow_mo=1000)

    if if_phone:
        phone = p.devices['iPhone 12 Pro']
        context = browser.new_context(**phone, permissions=permissions, reduced_motion='no-preference')
    else:
        context = browser.new_context()

    page = context.new_page()

    page.goto(TEST_URL, timeout=10000)

    phone_or_email_input = page.locator('input[type="email"]')
    expect(phone_or_email_input).to_be_visible()
    phone_or_email_input.fill(user_info["email"])

    continue_button = page.locator('button[tabindex="0"]')
    expect(continue_button).to_be_visible()
    continue_button.click()

    # Step 2: Click Join button if the user is new. Or, use Magic Code to sign in if the user is existing.
    wait(page)

    join_button = page.locator('button:has-text("Join")')
    wait(page)
    if join_button.count() > 0:
        join_button.click()
    else:
        magic_code = get_magic_code(user_info["email"], user_info["password"], retries=3, delay=10)
        print(f"Magic code: {magic_code}")

        validate_code_input = page.locator('input[data-testid="validateCode"]')
        expect(validate_code_input).to_be_visible()
        validate_code_input.fill(magic_code)

    return browser, page, context


def add_member(page):
    page.locator('button[aria-label="Navigates to a chat"]').nth(1).click()
    page.wait_for_timeout(1000)
    page.get_by_label("Create").nth(1).click()
    page.wait_for_timeout(1000)
    page.get_by_text("Track expense").click()
    page.wait_for_timeout(1000)
    page.get_by_label("Manual").click()
    page.wait_for_timeout(1000)
    page.get_by_placeholder("0").fill("100")
    page.wait_for_timeout(1000)
    page.locator("#numPadContainerView").get_by_role("button", name="Next").click()
    page.wait_for_timeout(1000)
    page.get_by_text("Description").click()
    page.wait_for_timeout(1000)
    page.get_by_test_id("IOURequestStepDescription").get_by_label("Back").click()
    page.wait_for_timeout(1000)
    page.get_by_label("Show more").click()
    page.wait_for_timeout(1000)
    page.get_by_text("Merchant").last.click()
    page.wait_for_timeout(1000)
    page.get_by_role("textbox", name="Merchant").fill("Test")
    page.wait_for_timeout(1000)
    page.get_by_role("button", name="Save").click()
    page.wait_for_timeout(1000)
    current_url = page.url
    page1 = page.context.new_page()  
    
    page1.goto(current_url)

    page.wait_for_timeout(1000)
    page.get_by_role("button", name="Track expense").click()
    page.wait_for_timeout(1000)
    page1.get_by_role("button", name="Track expense").click()
    page1.wait_for_timeout(1000)
    assert page1.get_by_text("Please select a participant.").is_visible()
    page1.close()
    page.wait_for_timeout(1000)
    page.get_by_label("Create").nth(1).click()
    page.wait_for_timeout(1000)
    page.get_by_text("Assign task").click()
    page.wait_for_timeout(1000)
    page.get_by_role("textbox", name="Title").fill("Task")
    page.wait_for_timeout(1000)
    page.get_by_role("button", name="Next").click()
    page.wait_for_timeout(1000)
    page2 = page.context.new_page()
    page.wait_for_timeout(1000)  
    page2.goto("https://dev.new.expensify.com:8082/new/task")
    page2.wait_for_timeout(1000)
    page.get_by_role("button", name="Confirm task").click()
    page.wait_for_timeout(1000)
    page2.get_by_role("button", name="Confirm task").click()
    page2.wait_for_timeout(1000)
    assert page2.get_by_text("Please enter a title and").is_visible()



def test_run():
    with sync_playwright() as p:
        # Step 1: Login
        seed = 11
        user_info = get_test_user_info(seed) # TODO Use any seed that you like 
        browser, page, context = login(p, user_info, False)

        # Step 2: Skip onboarding/start pages if any
        choose_what_to_do_today_if_any(page, TodayOptions.SOMETHING_ELSE, **user_info)
        add_member(page)

        browser.close()

