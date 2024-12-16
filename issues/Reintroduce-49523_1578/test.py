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

TEST_URL = "https://dev.new.expensify.com:8082"
USER_NAME = "swer49523record"
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
    # Step 2: Click Join button if the user is new. Or, use Magic Code to sign in if the user is existing.
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


def select_currency(page, currency: str = "USD", currency_symbol: str = "$"):
    currency_icon = page.locator('button[aria-label="Select a currency"]').last
    expect(currency_icon).to_be_visible()
    currency_icon.click()

    search_textbox = page.locator('input[aria-label="Search"]')
    expect(search_textbox).to_be_visible()
    search_textbox.fill(currency)

    currency_button = page.locator(f'button[aria-label="{currency} - {currency_symbol}"]').last
    expect(currency_button).to_be_visible()
    currency_button.click()


def pay_to_user(page):
    plus_create_icon = page.locator('button[aria-label="Create"]').last
    expect(plus_create_icon).to_be_visible()
    plus_create_icon.click()
    wait(page)
    try:
        pay_user_button = page.locator(f'div[aria-label="Pay milan@gmail.com"][role="menuitem"]')
        expect(pay_user_button).to_be_visible()
        pay_user_button.click()
    except:
        pay_user_button = page.locator(f'div[aria-label="Pay Hidden"][role="menuitem"]')
        expect(pay_user_button).to_be_visible()
        pay_user_button.click()
    wait(page)

    select_currency(page, currency="USD", currency_symbol="$")
    page.locator('input[role="presentation"]').last.fill("10")
    wait(page)
    next_button = page.locator('button[data-listener="Enter"]', has_text="Next").last
    expect(next_button).to_be_visible()
    next_button.click()
    wait(page)

    pay_elsewhere_button = page.locator('button', has_text="Pay with Expensify")
    expect(pay_elsewhere_button).to_be_visible()
    pay_elsewhere_button.click()
    wait(page)


def validate_pay_with_expensify_page(page):
    error_page = page.locator('div[dir="auto"]', has_text="Hmm... it's not here").last
    expect(error_page).not_to_be_visible()

    valid_page = page.locator('div[dir="auto"]', has_text="This feature requires you to validate your account.").last
    expect(valid_page).to_be_visible()


def start_chat_with_new_user(page):
    start_button = page.locator("button[aria-label='Start chat (Floating action)']")
    expect(start_button).to_be_visible()
    start_button.click()
    wait(page)
    start_chat_div = page.locator("div[role='menuitem'][aria-label='Start chat']")
    expect(start_chat_div).to_be_visible()
    start_chat_div.click()
    wait(page)
    invite_textbox = page.locator("input[aria-label='Name, email, or phone number']").locator("visible=true")
    invite_textbox.fill("milan@gmail.com")
    wait(page)
    user_button = page.locator("button[aria-label='milan@gmail.com']", has_text='milan@gmail.com').last
    expect(user_button).to_be_visible()
    user_button.click()
    wait(page)


def test_49523():
    with sync_playwright() as p:
        user_info = get_test_user_info(seed=8)
        # Step 1: Login
        browser, page = login(p, user_info, False)
        # Step 2: Skip onboarding/start pages if any
        choose_what_to_do_today_if_any(page, TodayOptions.SOMETHING_ELSE, **user_info)
        # A new user will see this Get Started link on the first logon.
        choose_link_if_any(page, "Get started")
        # Somehow the user can be redirected to the not-found page. This step redirects the user back to the home page.
        choose_link_if_any(page, "Go back to home page")

        start_chat_with_new_user(page)

        pay_to_user(page)

        validate_pay_with_expensify_page(page)

        wait(page)