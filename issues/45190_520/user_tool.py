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
import numpy as np
from PIL import Image
import io
from utils.trace_cleaner import trace_cleaner

GMAIL_NAME = "testerbro7077"
GMAIL_APP_PASSWORD = "xqxz mmcb tvkn lpgp"

def get_test_user_info(seed=None, first_name=None, last_name=None):
    if first_name is None:
        first_name = "Yagan"

    if last_name is None:
        last_name = "Sai"

    email = f"{GMAIL_NAME}+{seed}@gmail.com" if seed is not None else f"{GMAIL_NAME}@gmail.com"
    return {"email": email, "password": GMAIL_APP_PASSWORD, "first_name": first_name, "last_name": last_name}

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
    page.goto('https://dev.new.expensify.com:8082/')
    page.wait_for_load_state('load')

    try:
        expect(page.get_by_label("Inbox")).to_be_visible(timeout=3000)
        return
    except:
        pass

    page.get_by_test_id("username").fill(user_info["email"])
    page.get_by_role("button", name="Continue").click()

    join_button = page.get_by_role("button", name="Join")
    validate_code_input = page.locator('input[data-testid="validateCode"]')
    expect(join_button.or_(validate_code_input)).to_be_visible()

    if join_button.is_visible():
        join_button.click(timeout=3000)
    else:
        magic_code = "123456" #get_magic_code(user_info["email"], user_info["password"], retries=6, delay=5)
        print(f"Magic code: {magic_code}")
        validate_code_input.fill(magic_code)

    page.wait_for_timeout(3000)

    select_activity_dialog = page.get_by_text("What do you want to do today?")
    if select_activity_dialog.count() > 0:
        select_activity(page, user_info["first_name"], user_info["last_name"], activity_text)

def chech_bg_color(page):
    page.get_by_label("My settings").click()
    page.wait_for_timeout(1000)
    page.get_by_text("Preferences").click()
    page.wait_for_timeout(1000)
    if page.get_by_text("Dark").is_visible():
        pass
    else:
        page.get_by_text("Theme").click()
        page.get_by_label("Dark").click()

    page.get_by_test_id("CustomBottomTabNavigator").get_by_label("Search").click()
    page.get_by_role("button", name="Outstanding").click()
    checkbox = page.get_by_role("checkbox").nth(3)
    aria_checked = checkbox.get_attribute("aria-checked")
    page.wait_for_timeout(500)

    if aria_checked == "false":
        checkbox.click()
    else:
        checkbox.click()
        page.wait_for_timeout(500)
        checkbox.click()

    page.wait_for_timeout(1000)
    page.mouse.click(0.5, 0.5)

    page.wait_for_timeout(1000)
    view_button = page.get_by_role("button", name="View", exact=True).nth(2)
    container = view_button.locator("..").locator("..").locator("..").locator("..")
    background_color = container.evaluate("element => getComputedStyle(element).backgroundColor")

    expected_background_color = "rgb(26, 61, 50)"
    assert background_color == expected_background_color, "Expected background UI change did not occur"

def test_login():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=[
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
            "--ignore-certificate-errors"
        ])
        userA_info = get_test_user_info(seed=1, first_name="Yagna")
        contextA = browser.new_context()
        contextA.tracing.start(screenshots=True, snapshots=True, sources=True)
        pageA = contextA.new_page()
        try:
            login_user(pageA, userA_info)
            chech_bg_color(pageA)
        except Exception as e:
            print("Test failed due to exception:", e)
            raise
        finally:
            contextA.tracing.stop()
            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            contextA.tracing.export(path=trace_path)
            trace_cleaner(trace_path)
            pageA.close()
            contextA.close()
            browser.close()
