import os

import re, time
from datetime import datetime, timezone
from email.header import decode_header
from PIL import Image
from io import BytesIO
import imaplib
import email
import re
from playwright.sync_api import  Page, TimeoutError, expect, sync_playwright

USERNAME = "contributer0"
APP_PASSWORD = "ughk jfyj dyee mgrs"
USER_EMAIL = f"{USERNAME}+51355@gmail.com"
NEW_DOT_URL = "https://dev.new.expensify.com:8082/"


def get_magic_code(user_email, password, since=None, retries=5, delay=10):
    if since is None:
        since = datetime.now(timezone.utc).replace(second=0, microsecond=0)

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
                        email_date = email.utils.parsedate_to_datetime(msg["Date"])
                        if match and email_date >= since:
                            code = match.group(1)
                            imap.logout()
                            return code
                print("Email doesn't match conditions.  Retrying...")
            else:
                print("No unread emails found with the subject. Retrying...")
        else:
            print("Failed to retrieve emails. Retrying...")
        time.sleep(delay)

    imap.logout()
    print("Max retries reached. Email not found.")
    return None


def create_user(page: Page, firstname: str = "User", lastname: str = "Test"):
    page.get_by_role("button", name="Join").click()

    # Update profile
    page.get_by_text("Track and budget expenses").click()
    page.get_by_role("button", name="Continue").last.click()
    page.get_by_role("textbox", name="First name").fill(firstname)
    page.get_by_role("textbox", name="Last name").fill(lastname)

    try:
        page.get_by_role("button", name="Continue").click(timeout=2000)
    except TimeoutError:
        pass

    try:
        page.get_by_role("button", name="Get Started").click(timeout=200)
    except TimeoutError:
        pass



def login(page: Page):
    # get current timestamp
    page.wait_for_timeout(2000)
    magic_code = "123456" 

    if magic_code is None:
        raise ValueError("Failed to retrieve magic code")
    page.get_by_role("textbox").fill(magic_code)

def login_or_create_user(
    page: Page, user_email: str = USER_EMAIL, lastname: str = "Test"
):
    page.get_by_role("textbox", name="Phone or email").fill(user_email)
    page.get_by_role("button", name="Continue").click()

    try:
        page.get_by_role("button", name="Join").wait_for(state="visible", timeout=2000)
        create_user(page, lastname)
    except TimeoutError:
        login(page)

    page.get_by_label("Inbox").first.wait_for(state="visible")


def create_sample_jpg():
    # Generates an image in memory and returns the bytes
    image = Image.new("RGB", (100, 100), color="blue")
    img_byte_arr = BytesIO()
    image.save(img_byte_arr, format="JPEG")
    img_byte_arr.seek(0)
    return img_byte_arr.getvalue()

def test_51355():
    with sync_playwright() as p:

        # Launch chromium and open new page
        browser = p.chromium.launch(
            channel="chrome",
            headless=False,
            args=[
                "--ignore-certificate-errors",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process"
            ],
            proxy={"server": "http://localhost:8080"},
            slow_mo=500
        )
        context = browser.new_context()
        page = context.new_page()

        # Login Expensify
        page.goto(NEW_DOT_URL)
        login_or_create_user(page)

        # go to Settings
        page.get_by_label("My settings").click()

        # go to profile
        page.get_by_role("menuitem", name="Profile").click()
        
        regular_button = page.get_by_label("Share code").locator("svg")
        regular_button_width = regular_button.get_attribute("width")
        regular_button_hight = regular_button.get_attribute("height")

        # click on edit photo
        with page.expect_file_chooser() as fc_info:
            page.get_by_label("Edit photo").click()

        file_chooser = fc_info.value
        file_chooser.set_files({
            "name": "input.jpg",
            "mimeType": "image/jpeg",
            "buffer": create_sample_jpg()

        })

        rotate_button = page.get_by_test_id("AvatarCropModal").get_by_role("button").nth(1)
        icon_element = rotate_button.locator("svg")


        # check that the Icon is the same size as regular button
        assert icon_element.get_attribute("width") == regular_button_width
        assert icon_element.get_attribute("height") == regular_button_hight
        