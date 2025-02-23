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
from datetime import datetime, timezone



TEST_URL = "https://dev.new.expensify.com:8082/" # TODO Use the URL that works in your local development. For example, it can be 'https://dev.new.expensify.com:8082/'













USER_NAME = "expensify31" # TODO Change this to your Gmail username
USER_PASSWORD = "Pass@123456" # TODO Change this to your password



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
        return {"email": f"{USER_NAME}@gmail.com", "password": USER_PASSWORD, "first_name": f"{USER_NAME}", "last_name": "Test"}
    
    if type(seed) == type(True):
        seed = int(time.time())

    return {"email": f"{USER_NAME}+{seed}@gmail.com", "password": USER_PASSWORD, "first_name": f"Test", "last_name": "User"}

def wait(page, for_seconds=1):
    page.wait_for_timeout(for_seconds * 1000)





def get_magic_code(user_email, password, retries=5, delay=10, since=None):
    if since is None:
        since = datetime.now(timezone.utc).replace(second=0, microsecond=0)

    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    imap.login("expensify31@gmail.com", "glss akzu qghd ylad")

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


                        match = re.search(r"Expensify magic sign-in code: (\d+)", subject)
                        email_date = email.utils.parsedate_to_datetime(msg["Date"])
                        if match and email_date >= since:
                            code = match.group(1)
                            imap.logout()
                            return code
            else:
                print("No unread emails found with the subject. Retrying...")
        else:
            print("Failed to retrieve emails. Retrying...")


        time.sleep(delay)

    imap.logout()
    print("Max retries reached. Email not found.")
    return None

def choose_what_to_do_today_if_any(page, option: TodayOptions, retries = 5, **kwargs):
    wait(page)

    for _ in range(retries):
        wdyw = page.locator("text=What do you want to do today?")
        if wdyw.count() == 0:
            print('"What do you want to do today?" dialog is not found. Wait and retry...')
            wait(page)
        else:
            break

    if wdyw.count() == 0:
        print('"What do you want to do today?" dialog is not found.')
        return 
    
    expect(wdyw).to_be_visible()
        
    if option == TodayOptions.SOMETHING_ELSE:
        text = "Something else"
    elif option == TodayOptions.TRACK_AND_BUDGET_EXPENSES:
        text='Track and budget expenses'

    page.locator(f"text='{text}'").click()
    page.get_by_role("button", name="Continue").click()


    wait(page)
    page.locator('input[name="fname"]').fill(kwargs['first_name'])
    page.locator('input[name="lname"]').fill(kwargs['last_name'])
    page.get_by_role("button", name="Continue").last.click()

def choose_link_if_any(page, link_text, retries = 5):
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


def login(p: PlaywrightContextManager, user_info, if_phone=False) -> tuple[Browser, Page, str]:  
    
    login_time = datetime.now(timezone.utc).replace(second=0, microsecond=0)  

    permissions = ['clipboard-read', 'clipboard-write']

    proxy = {"server": "http://127.0.0.1:8080/"}
    args = ["--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"]
    browser = p.chromium.launch(headless=True, args=args)

    if if_phone:
        phone = p.devices['iPhone 12 Pro']
        context = browser.new_context(**phone, permissions=permissions, reduced_motion='no-preference')
    else:
        context = browser.new_context()

    page = context.new_page()

    page.goto(TEST_URL, timeout=120000) # Timeout is set to 120 seconds to avoid a Timeout error in my environment - native MacOS M1 Max. Perhaps you can set it to a lower value if you have a faster environment.

    phone_or_email_input = page.locator('input[type="email"]')
    expect(phone_or_email_input).to_be_visible()
    phone_or_email_input.fill(user_info["email"])

    continue_button = page.locator('button[tabindex="0"]')
    expect(continue_button).to_be_visible()
    continue_button.click()


    wait(page)

    join_button = page.locator('button:has-text("Join")')
    if join_button.count() > 0:
        print("Join button found. This is a new user.")
        join_button.click()
    else:
        print("Join button not found. This is an existing user. Use Magic Code to sign in.")
        magic_code = get_magic_code(user_info["email"], user_info["password"], retries=5, delay=10, since=login_time)
        print(f"Magic code: {magic_code}")
        page.wait_for_timeout(2000)
        magic_code= "123456"

        validate_code_input = page.locator('input[data-testid="validateCode"]')
        expect(validate_code_input).to_be_visible()
        validate_code_input.fill(magic_code)






    return browser, page




        

def test():
    with sync_playwright() as p:

        user_info = get_test_user_info(seed=None) # TODO Use any seed that you like 
        browser, page = login(p, user_info, True)
        choose_what_to_do_today_if_any(page, TodayOptions.SOMETHING_ELSE, **user_info)
        choose_link_if_any(page, "Get started") # A new user will see this Get Started link on the first logon.
        page.wait_for_timeout(2000)
        page.get_by_label("My settings").click()
        page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").get_by_text("Workspaces").click()
        page.get_by_label("New workspace").click()
        page.get_by_text("More features").click()
        page.wait_for_timeout(2000)
        page.get_by_label("Document and reclaim eligible").click()
        page.get_by_test_id("WorkspaceInitialPage").get_by_text("Taxes").click()
        page.get_by_role("button", name="Add rate").click()
        page.get_by_test_id("WorkspaceCreateTaxPage").get_by_text("Name").click()
        page.get_by_role("textbox", name="Name").fill("TestTax2")
        page.get_by_test_id("TextSelectorModal").get_by_role("button", name="Save").click()
        page.get_by_text("Value").click()
        page.get_by_placeholder("0").click()
        page.get_by_placeholder("0").fill("24")
        page.get_by_test_id("AmountSelectorModal").get_by_role("button", name="Save").click()
        page.wait_for_timeout(2000)
        page.get_by_role("button", name="Save").click()
        page.wait_for_timeout(2000)
        page.locator("#id_TESTTAX2").click()
        page.wait_for_timeout(2000)
        page.get_by_test_id("WorkspaceEditTaxPage").get_by_label("TestTax2").get_by_text("TestTax2").click()
        page.wait_for_timeout(2000)
        page.get_by_role("button", name="Save").click()
        page.wait_for_timeout(2000)

        error_selector = "text=An error occurred while"

        expect(page.locator(error_selector)).not_to_be_visible(timeout=100)
       
        browser.close()
