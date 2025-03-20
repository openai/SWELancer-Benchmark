import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
from playwright.sync_api import Page, expect, sync_playwright
import imaplib
import email
import re
from email.header import decode_header
import pytest

GMAIL_NAME = "rgulraiz2000"
GMAIL_APP_PASSWORD = ""


def get_test_user_info(seed = None, first_name = None, last_name = None):
    if first_name is None:
        first_name = GMAIL_NAME

    if last_name is None:
        last_name = ""

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
    page.wait_for_timeout(3000)

    page.get_by_role("textbox", name="Phone or email").click()
    page.get_by_role("textbox", name="Phone or email").fill(user_info["email"])
    page.get_by_role("button", name="Continue").click()
    
    join_button = page.get_by_role("button", name="Join")
    validate_code_input = page.locator('input[data-testid="validateCode"]')
    validate_code_input = page.locator('input[name="validateCode"]')
    validate_code_input = page.locator('input[autocomplete="one-time-code"][maxlength="6"]')

    expect(validate_code_input).to_be_visible()

    if (join_button.is_visible()):
        join_button.click(timeout=3000)
    else:

        magic_code = "123456"
        validate_code_input.fill(magic_code)

    page.wait_for_timeout(3000)


def test_track_sound():

    with sync_playwright() as p:
        timestamp = int(time.time())


        browser = p.chromium.launch(headless=True,args=[
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ])
        context = browser.new_context()
        page = context.new_page()

        URL = "https://dev.new.expensify.com:8082/"
 

        user_info = get_test_user_info(first_name="John", last_name="T")
        login_user(page, user_info, URL)
        page.wait_for_timeout(4000)
        page.get_by_label("Start chat (Floating action)").click()
        page.get_by_label("Track expense").click()
        page.get_by_role("button", name="Got it").click()
        page.get_by_label("Manual").click()
        page.get_by_placeholder("0").fill("1000")
        page.locator("#numPadContainerView").get_by_role("button", name="Next").click()
        page.get_by_label("Show more").click()
        page.get_by_role("menuitem", name="Merchant").click()
        page.get_by_role("textbox", name="Merchant").fill("merchant_1")
        page.get_by_role("button", name="Save").click()


        page.evaluate(
            """
          () => {
            window.soundPlayCount = 0;
            const originalPlay = Sound.prototype.create;
            Sound.prototype.create = function() {
              originalPlay.call(this);
              window.soundPlayCount++;
            };
          }
        """
        )

        page.get_by_role("button", name="Track expense").click()
        page.wait_for_timeout(2000)


        sound_play_count = page.evaluate("window.soundPlayCount")


        assert sound_play_count == 1, "Sound was not played once"


        context.close()
        browser.close()

