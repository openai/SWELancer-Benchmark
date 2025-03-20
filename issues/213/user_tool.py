import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
import imaplib
import email
from email.header import decode_header
import re
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page

from utils.trace_cleaner import trace_cleaner


GMAIL_NAME = 'rgulraiz2000'
GMAIL_APP_PASSWORD = ''


def get_test_user_info(seed = None, first_name = None, last_name = None):
    if first_name is None:
        first_name = GMAIL_NAME

    if last_name is None:
        last_name = ""

    email = f"{GMAIL_NAME}+{seed}@gmail.com" if seed is not None else f"{GMAIL_NAME}@gmail.com"
    
    return {"email": email, "password": GMAIL_APP_PASSWORD, "first_name": first_name, "last_name": last_name}


def get_magic_code(user_email, password, retries=5, delay=10):
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

                        match = re.search(r"Expensify magic sign-in code: (\d+)", subject)
                        if match:
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


def login_user(page, user_info, URL):
    page.goto(URL)
    page.wait_for_timeout(5000)

    page.get_by_role("textbox", name="Phone or email").click()
    page.get_by_role("textbox", name="Phone or email").fill(user_info["email"])
    page.wait_for_timeout(8000)
    page.get_by_role("button", name="Continue").click()
    page.wait_for_timeout(3000)

    join_button = page.get_by_role("button", name="Join")
    

    if (join_button.is_visible()):
        join_button.click(timeout=3000)
    else:
        page.wait_for_timeout(1000)
        validate_code_input = page.locator('input[data-testid="validateCode"]')
        validate_code_input = page.locator('input[name="validateCode"]')
        validate_code_input = page.locator('input[autocomplete="one-time-code"][maxlength="6"]')
        expect(validate_code_input).to_be_visible()

        magic_code = "111000"
        validate_code_input.fill(magic_code)

    page.wait_for_timeout(8000)

    if page.get_by_text("Track and budget expenses").is_visible():
        page.get_by_text("Track and budget expenses").click()
        page.get_by_role("textbox", name="First name").fill(user_info["first_name"])
        page.get_by_role("textbox", name="Last name").fill(user_info["last_name"])
        page.get_by_role("button", name="Continue").click()


def submit_expense_in_workspace_chat(browser, page, user_info, number, amount="1000"):

    workspace_chat = page.locator('button[aria-label="Navigates to a chat"]', has_text=f"{user_info['first_name']} {user_info['last_name']}'s Workspace {number}")
    if workspace_chat.count() > 1:
        workspace_chat.first.click()
    else:
        workspace_chat.click()
    page.wait_for_timeout(1000)


    plus_create_icon = page.locator('button[aria-label="Create"]').last
    plus_create_icon.click()
    page.wait_for_timeout(1000)

    submit_expense_button = page.locator('div[aria-label="Submit expense"]')
    submit_expense_button.click()
    page.wait_for_timeout(1000)


    manual_button = page.locator('button[aria-label="Manual"]')
    manual_button.click()
    page.wait_for_timeout(1000)

    page.locator('input[role="presentation"]').fill(amount)


    next_button = page.locator('button[data-listener="Enter"]', has_text="Next").first
    next_button.click()
    page.wait_for_timeout(1000)


    merchant_field = page.locator('div[role="menuitem"]', has_text="Merchant")
    merchant_field.click()
    page.wait_for_timeout(1000)

    page.locator('input[aria-label="Merchant"]').fill("GM Merchant")

    save_button = page.locator('button', has_text="Save")
    save_button.click()
    page.wait_for_timeout(1000)


    save_button = page.locator('button[data-listener="Enter"]', has_text="Submit")
    save_button.click()
    page.wait_for_timeout(1000)

    return browser, page

def get_workspace_number(page:Page):

    workspace_text = page.get_by_test_id("report-actions-list").last.inner_text()


    match = re.search(r"\d+", workspace_text)
    number = match.group() if match else ""

    return number


def test_search_selection_persists():
    with sync_playwright() as p:
        user_first_name = "Khan"
        user_last_name = "G"
        

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


        context = browser.new_context()
        context.tracing.start(screenshots=True, snapshots=True)
        page = context.new_page()

        try:

            user_info = get_test_user_info(seed=331133, first_name=user_first_name, last_name=user_last_name)
            login_user(page, user_info, "https://dev.new.expensify.com:8082/")
            page.wait_for_timeout(6000)


            page.get_by_label("My settings").click()
            page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()
            page.get_by_label("New workspace").first.click()
            page.locator('button[aria-label="Back"]').click()
            inbox_menu = page.locator('button[aria-label="Inbox"]')
            inbox_menu.click()
            page.wait_for_timeout(2000)


            workspace_number = get_workspace_number(page)
            submit_expense_in_workspace_chat(browser, page, user_info, workspace_number)


            search_expense = page.locator('button[aria-label="Search"]')
            expect(search_expense).to_be_visible()
            search_expense.click()
            page.wait_for_timeout(6000)
            checkbox = page.locator('div[role="checkbox"][data-tag="pressable"]')
            if checkbox.count() > 1:
                expect(checkbox.last).to_be_visible()
                checkbox.last.click()
            else:
                checkbox.click()

            page.wait_for_timeout(6000)
            inbox = page.locator('button[aria-label="Inbox"]')
            expect(inbox).to_be_visible()
            inbox.click()


            page.get_by_label("Expense Report #").nth(1).click()
            page.get_by_label("Delete expense").click()
            page.wait_for_timeout(1000)
            page.locator('button:has-text("Delete")').click()


            search_expense_ = page.locator('button[aria-label="Search"]')
            expect(search_expense_).to_be_visible()
            search_expense_.click()

            is_selected = page.get_by_text('1 selected')
            if is_selected.is_visible():
                assert False, 'Search selection is not resetted after deleting an expense.'
            else:
                assert True, 'Search selection is resetted after deleting an expense.'

            page.wait_for_timeout(2000)
        except Exception as e:

            raise e
        finally:

            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            browser.close()
