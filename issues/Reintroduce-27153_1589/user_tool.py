import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
import imaplib
import email
import re
from email.header import decode_header
from playwright.sync_api import sync_playwright, expect
from utils.trace_cleaner import trace_cleaner

GMAIL_NAME = "testerbro7077"
GMAIL_APP_PASSWORD = "xqxz mmcb tvkn lpgp"

def get_test_user_info(seed=None, first_name=None, last_name=None):
    if first_name is None:
        first_name = "Yagan"

    if last_name is None:
        last_name = "Sai"

    # Build the email
    mail_addr = f"{GMAIL_NAME}+{seed}@gmail.com" if seed is not None else f"{GMAIL_NAME}@gmail.com"
    return {
        "email": mail_addr,
        "password": GMAIL_APP_PASSWORD,
        "first_name": first_name,
        "last_name": last_name
    }

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
    page.goto('http://localhost:8082')
    page.wait_for_load_state('load')

    page.get_by_role("textbox", name="Phone or email").fill(user_info["email"])
    page.get_by_role("button", name="Continue").click()

    validate_code_input = page.locator('input[name="validateCode"]').first
    expect(validate_code_input).to_be_visible()

    # Hard-coded code for demonstration
    validate_code_input.fill("235646")

    page.wait_for_timeout(3000)

def check_scroll(page):
    page.get_by_test_id("6978374583921682").click()
    page.get_by_role("button", name="Actions").click()
    page.get_by_role("textbox", name="Write something...").click()
    page.get_by_role("textbox", name="Write something...").fill("*Lorem Ipsum*\u00a0is simply dummy text of the printing and typesetting industry. Lorem Ipsum has been the industry's standard dummy text ever since the 1500s, when an unknown printer took a galley of type and scrambled it to make a type specimen book. It has survived not only five centuries, but also the leap into electronic typesetting, remaining essentially unchanged. It was popularised in the 1960s with the release of Letraset sheets containing Lorem Ipsum passages, and more recently with desktop publishing software like Aldus PageMaker including versions of Lorem Ipsum.\n*Lorem Ipsum*\u00a0is simply dummy text of the printing and typesetting industry.\n*Lorem Ipsum*\u00a0is simply dummy text of the printing and typesetting industry.\n*Lorem Ipsum*\u00a0is simply dummy text of the printing and typesetting industry.\n*Lorem Ipsum*\u00a0is simply dummy text of the printing and typesetting industry.\n*Lorem Ipsum*\u00a0is simply dummy text of the printing and typesetting industry.\n")
    page.wait_for_timeout(2000)
    page.reload()
    page.wait_for_timeout(1000)

    textarea = page.locator('textarea.css-textinput-11aywtz')
    is_at_bottom = textarea.evaluate("""
        element => element.scrollTop + element.clientHeight >= element.scrollHeight
    """)

    # Assert that the scroll is at the bottom
    assert is_at_bottom, "App maintains focus but does not scroll to bottom at cursor position in compose box"

def test_login():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="chrome",
            headless=True,
            args=["--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"]
        )
        # Create context and begin tracing.
        contextA = browser.new_context()
        contextA.tracing.start(title="traceA", screenshots=True, snapshots=True)

        # We'll ensure the trace is exported even if an error occurs.
        pageA = contextA.new_page()
        try:
            userA_info = get_test_user_info(seed=2, first_name="Yagna")
            login_user(pageA, userA_info)
            check_scroll(pageA)
        except Exception as e:
            raise e
        finally:
            # Stop the trace, export it, and clean it, even if the test failed.
            contextA.tracing.stop()
            contextA.tracing.export("/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            pageA.close()
            contextA.close()
            browser.close()
