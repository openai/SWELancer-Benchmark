import os

import re, time
from datetime import datetime, timezone
from email.header import decode_header
from PIL import Image
from io import BytesIO
import imaplib
import email
import re
from playwright.sync_api import Page, TimeoutError, expect, sync_playwright
from utils.trace_cleaner import trace_cleaner

USERNAME = "contributer0"
APP_PASSWORD = ""
USER_EMAIL = f"{USERNAME}+51388_1@gmail.com"
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


def test_51388():
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
        # mobile_device = p.devices['Pixel 7']
        mobile_device = p.devices['iPhone 12 Pro']
        context = browser.new_context(**mobile_device)
        
        # Start tracing
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        
        page = context.new_page()

        try:
            # Login Expensify
            page.goto(NEW_DOT_URL)
            login_or_create_user(page)

            # go to Settings
            page.get_by_label("My settings").click()

            # enable debug mode 
            page.get_by_label("Troubleshoot").click()
            page.get_by_label("Debug mode").click()
            page.get_by_label("Back").click()
            page.wait_for_timeout(1000)

            # create a new workspace
            page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()
            page.get_by_label("New workspace").first.click()
            page.get_by_test_id("WorkspaceInitialPage").get_by_label("Profile").click()
            page.get_by_label("Test User's Workspace").last.click()
            workspace_name = f"workspace{3456}"
            page.get_by_role("textbox", name="Name").fill(workspace_name)
            page.get_by_role("button", name="Save").click()
            page.wait_for_timeout(1000)
            page.get_by_test_id("WorkspacePageWithSections").get_by_label("Back").click()
            page.get_by_test_id("WorkspaceInitialPage").get_by_label("Back").click()
            page.get_by_test_id("WorkspacesListPage").get_by_label("Back").click()

            page.get_by_label("Inbox").click()

            page.get_by_label("Navigates to a chat").get_by_text(workspace_name).last.click()

            # send a message
            page.locator("#composer").fill("hello")
            page.get_by_label("Send").click()
        
            # Tap header 
            try:
                page.get_by_label(workspace_name).click(timeout=5000)
            except:
                page.get_by_label("Test User").click(timeout=5000)
        
            # press debug
            page.get_by_label("Debug").click()
        
            # tap delete
            page.get_by_role("button", name="Delete").click()
            page.get_by_label("Back").last.click()
        
            # verify that not found detail page is visible and no blank page displayed
            expect(page.get_by_text("Hmm... it's not here")).to_be_visible()
            page.reload()
            page.wait_for_timeout(1000)
            expect(page.get_by_text("Hmm... it's not here")).to_be_visible()
            page.wait_for_timeout(1000)

        finally:
            # Stop tracing, export the trace, clean it, and close the browser
            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            context.close()
            browser.close()
