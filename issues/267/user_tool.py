import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
import imaplib
import email
import re
import os
from email.header import decode_header
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from utils.trace_cleaner import trace_cleaner


GMAIL_NAME = "nomandevtur+50577"
GMAIL_APP_PASSWORD = "tpye xlsj axyq nltq"


def get_test_user_info(seed=None, first_name=None, last_name=None):
    if first_name is None:
        first_name = GMAIL_NAME

    if last_name is None:
        last_name = ""

    email_addr = f"{GMAIL_NAME}+{seed}@gmail.com" if seed is not None else f"{GMAIL_NAME}@gmail.com"
    
    return {"email": email_addr, "password": GMAIL_APP_PASSWORD, "first_name": first_name, "last_name": last_name}


def delete_email_inbox(user_email, password, retries=5, delay=10):
    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    imap.login(user_email, password)

    imap.select("inbox")
    status, all_emails = imap.search(None, "ALL")
    if status == "OK":
        for email_id in all_emails[0].split():
            imap.store(email_id, "+FLAGS", "\Deleted")
        imap.expunge()


def get_magic_code(user_email, password, retries=5, delay=5):

    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    imap.login(user_email, password)

    for _ in range(retries):
        imap.select("inbox")
        status, messages = imap.search(None, '(UNSEEN SUBJECT "Expensify magic sign-in code:")')

        if status == "OK":
            email_ids = messages[0].split()
            print(email_ids)

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


def select_activity(page, first_name, last_name, activity_text):
    expect(page.get_by_text("What do you want to do today?")).to_be_visible()
    

    page.get_by_label(activity_text).click()
    

    page.get_by_role("textbox", name="First name").fill(first_name)
    page.get_by_role("textbox", name="Last name").fill(last_name)
    page.get_by_role("button", name="Continue").last.click()


def login_user(page, user_info, activity_text="Track and budget expenses"):

    page.context.clear_cookies()

    page.goto('https://dev.new.expensify.com:8082/')
    page.wait_for_load_state('load')
    
    try:
        expect(page.get_by_label("Inbox")).to_be_visible(timeout=10000)
        return
    except:
        pass

    page.get_by_test_id("username").fill(user_info["email"])
    page.get_by_role("button", name="Continue").click()

    join_button = page.get_by_role("button", name="Join")
    validate_code_input = page.locator('input[data-testid="validateCode"]')
    expect(join_button.or_(validate_code_input)).to_be_visible()

    if (join_button.is_visible()):
        join_button.click(timeout=3000)
    else:
        magic_code = "123456"
        validate_code_input.fill(magic_code)

    page.wait_for_timeout(3000)

    select_activity_dialog = page.get_by_text("What do you want to do today?")
    if select_activity_dialog.count() > 0:
        select_activity(page, user_info["first_name"], user_info["last_name"], activity_text)


def get_context(p: PlaywrightContextManager, user_info, browser, is_phone_setup=False):
    """
    Creates and returns a browser context and the initial page.
    Supports mobile or desktop context setup.
    """
    permissions = ['clipboard-read', 'clipboard-write']

    data_dir = 'mobile_context' if is_phone_setup else 'desktop_context'
    data_dir += f"_{user_info['email']}"
    os.makedirs(data_dir, exist_ok=True)  

    context_options = {
        "permissions": permissions,
        "storage_state": None  
    }

    if is_phone_setup:
        context_options.update({
            "viewport": {"width": 390, "height": 844},  
            "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
        })

    context = browser.new_context(**context_options)
    page = context.new_page()
    return context, page

    

def test_inconsistent_button_behavior():
    with sync_playwright() as p:
        user_info = get_test_user_info(10)

        delete_email_inbox(user_info["email"], user_info["password"], retries=6, delay=5)

        browser = p.chromium.launch(channel="chrome", headless=True, slow_mo=500, args=[
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ])

        context, page = get_context(p, user_info, browser)
        # Start tracing
        context.tracing.start(screenshots=True, snapshots=True, sources=True)

        try:
            login_user(page, user_info)

            page.get_by_label("Start chat (Floating action)").click()
            page.get_by_label("Submit expense").nth(0).click()
            page.get_by_label("Manual").click()
            page.get_by_placeholder("0").fill("100")
            page.locator("#numPadContainerView").get_by_role("button", name="Next").click()

            page.get_by_test_id("selection-list").get_by_label("Nomandevtur+50577's Workspace").click()

            page.get_by_role("menuitem", name="Merchant Required").click()
            page.get_by_role("textbox", name="Merchant").fill("hello")
            page.get_by_role("button", name="Save").click()
            page1 = context.new_page()
            page1.bring_to_front()
            page1.goto(page.url)
            page1.wait_for_load_state('load')
            page.wait_for_timeout(5000)

            page.bring_to_front()
            page.get_by_role("button", name="Submit PKR").click()

            page.wait_for_timeout(1000)
            page1.bring_to_front()
            page1.get_by_role("button", name="Submit PKR").click()
            page.wait_for_timeout(1000)

            text_locator = page1.get_by_text("Please select a participant.")
            expect(text_locator).to_be_visible()

            page.bring_to_front()
            page.get_by_label("Create").click()
            page.get_by_label("Assign task").click()
            page.get_by_role("textbox", name="Title").fill("877")
            page.get_by_role("button", name="Next").click()

            page1.bring_to_front()
            page1.goto(page.url)
            page1.wait_for_load_state('load')

            page.wait_for_timeout(5000)

            page.bring_to_front()
            page.get_by_role("button", name="Confirm task").click()

            page.wait_for_timeout(1000)
            page1.bring_to_front()
            page1.get_by_role("button", name="Confirm task").click()
            page.wait_for_timeout(1000)
            
            text_locator = page1.get_by_text("Please enter a title and select a share destination.")
            expect(text_locator).to_be_visible()

            page.close()
        finally:
            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            context.tracing.stop(path=trace_path)
            trace_cleaner(trace_path)
            browser.close()


if __name__ == '__main__':
    test_inconsistent_button_behavior()
