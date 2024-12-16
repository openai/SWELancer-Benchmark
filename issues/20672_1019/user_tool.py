import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import os
import time
import imaplib
import email
from email.header import decode_header
from playwright.sync_api import Page, expect, sync_playwright
import re
from PIL import Image, ImageDraw, ImageFont

from utils.trace_cleaner import trace_cleaner  # <-- Added

GMAIL_NAME = "rgulraiz2000"
GMAIL_APP_PASSWORD = "kepw uquj myoa npvj"


def get_test_user_info(seed = None, first_name = None, last_name = None):
    if first_name is None:
        first_name = GMAIL_NAME

    if last_name is None:
        last_name = ""

    email = f"{GMAIL_NAME}+{seed}@gmail.com" if seed is not None else f"{GMAIL_NAME}@gmail.com"
    
    return {"email": email, "password": GMAIL_APP_PASSWORD, "first_name": first_name, "last_name": last_name}


def get_magic_code(user_email, password, retries=5, delay=5):
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

        # Wait for the specified delay before trying again
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
        # magic_code = get_magic_code(user_info["email"], user_info["password"], retries=6, delay=5)
        magic_code = "123456"
        validate_code_input.fill(magic_code)

    page.wait_for_timeout(3000)


def create_img():
    width, height = 400, 200
    image = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.text((100, 80), "This is Profile Picture", fill=(0, 0, 0))
    temp_file_path = "profile_pic.png"
    image.save(temp_file_path, format="PNG")
    return temp_file_path



def close_button_if_present(page: Page):
    """
    Occasionally, there is a close button that prevents any clicks on the page as
    it covers most of the screen. This button cannot be seen visually.
    """
    close_button = page.locator('button[aria-label="Close"]')
    if close_button.is_visible():
        close_button.click()


def test_tooltip_avatar():

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True,args=[
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ])
        context = browser.new_context()
        # Start Playwright tracing
        context.tracing.start(screenshots=True, snapshots=True, sources=True)

        try:
            page = context.new_page()
            user_info = get_test_user_info(seed=33110, first_name="John", last_name="K")
            login_user(page, user_info, "https://dev.new.expensify.com:8082/")

            # get the image to upload
            image_file_path = create_img()

            # create user
            first_name = "John"
            last_name = "K"

            # Send message to self
            close_button_if_present(page)

            page.get_by_text(f"{user_info['email']}").click()
            page.get_by_role("textbox").fill("Hey")
            page.keyboard.press("Enter")

            context.set_offline(True)
            
            # Set User Name
            page.get_by_label("My settings").click()
            page.get_by_text("Display name").click()
            page.get_by_role("textbox", name="First name").click()
            page.get_by_role("textbox", name="First name").fill(first_name)
            page.get_by_role("textbox", name="Last name").click()
            page.get_by_role("textbox", name="Last name").fill(last_name)
            page.get_by_role("button", name="Save").click()
            page.get_by_label("Inbox").click()

            # Update profile photo
            page.get_by_label("My settings").click()
            page.on(
                "filechooser", lambda file_chooser: file_chooser.set_files(image_file_path)
            )

            if page.get_by_label("Edit photo").count() > 1:
                page.get_by_label("Edit photo").last.click()
            else:
                page.get_by_label("Edit photo").click()    
            
            page.get_by_role("button", name="Save").click()

            # Open personal chat
            page.get_by_label("Inbox").click()
            page.wait_for_timeout(5000)  # wait for images to loads

            page.get_by_text(f"{first_name} {last_name} (you)").click()

            # Get the source of the avatar from the message we sent earlier
            avatar = page.get_by_role("button", name=user_info["email"]).first
            img_src = avatar.locator("img").get_attribute("src")

            images_count_before = page.locator(f'img[src="{img_src}"]').count()

            # Hover over profile photo to reveal tooltip
            # Tooltip should display one more avatar with the same image
            avatar.hover()

            page.wait_for_timeout(2000)  # wait for tooltip to render

            images_count_after = page.locator(f'img[src="{img_src}"]').count()

            assert (
                images_count_after == images_count_before + 1
            ), "Tooltip has different image from the avatar"

        except Exception as e:
            print("An error occurred in the test:", e)
            raise
        finally:
            # Stop and export the trace even if there's an error
            context.tracing.stop()
            context.tracing.export(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")

            context.close()
            browser.close()
