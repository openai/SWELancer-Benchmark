import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import email
import imaplib
import time
from io import BytesIO

from playwright._impl._page import Page
from playwright.sync_api import TimeoutError, expect, sync_playwright

from utils.trace_cleaner import trace_cleaner  # <-- Added import for trace_cleaner


EMAIL_USERNAME = "expensifytesting1@gmail.com"
EMAIL_PASSWORD = "redx tbmr hzpc rbzr"


EMAIL_USERNAME_POSTFIX = "43726"


def generate_user_email():
    """
    Generate an email address for a user login.
    """
    temp = EMAIL_USERNAME.rsplit("@", 1)
    username = temp[0].strip()
    domain = temp[1].strip()
    return f"{username}+{EMAIL_USERNAME_POSTFIX}@{domain}"


def clear_inbox(username, password):
    """
    Delete all the messages from the Inbox.
    """

    return
    with imaplib.IMAP4_SSL(host="imap.gmail.com") as imap:
        imap.login(username, password)
        imap.select("inbox")
        imap.store("1:*", "+FLAGS", "\\Deleted")
        imap.expunge()
        imap.close()


def get_otp_from_email(username, password, retries=12, delay=5):
    """
    Read the OTP email and return the OTP code.
    """

    return "123456"
    with imaplib.IMAP4_SSL(host="imap.gmail.com") as imap:
        imap.login(username, password)
        for i in range(1, retries + 1):
            imap.select("inbox")
            status, messages = imap.search(None, "ALL")
            if status == "OK":
                for message_id in reversed(messages[0].split()):
                    status, data = imap.fetch(message_id, "(RFC822)")
                    if status == "OK":
                        email_message = email.message_from_bytes(data[0][1])
                        subject, encoding = email.header.decode_header(email_message["Subject"])[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding)
                        if subject.startswith("Expensify magic sign-in code:"):
                            otp_code = subject.split(":")[-1].strip()
                            return otp_code
            time.sleep(delay)
        imap.close()
    raise AssertionError("Failed to read the OTP from the email")


def login_user(page: Page, first_name="Milan", last_name="T"):

    user_email = generate_user_email()


    page.goto("https://dev.new.expensify.com:8082/")


    clear_inbox(EMAIL_USERNAME, EMAIL_PASSWORD)
    page.locator('input[type="email"]').fill(user_email)
    page.locator("button", has_text="Continue").click()


    try:
        expect(page.get_by_test_id("SignInPage").get_by_test_id("validateCode")).to_be_visible(timeout=5000)
    except AssertionError:

        page.get_by_test_id("SignInPage").get_by_role("button", name="Join").click()
    else:

        otp_code = get_otp_from_email(EMAIL_USERNAME, EMAIL_PASSWORD)
        page.get_by_test_id("SignInPage").get_by_test_id("validateCode").fill(otp_code)
        try:
            page.get_by_test_id("SignInPage").get_by_role("button", name="Sign in").click(timeout=3000)
        except (AssertionError, TimeoutError):
            pass

    try:
        expect(page.get_by_text("What do you want to do today?")).to_be_visible(timeout=5000)
    except AssertionError:
        pass
    else:

        page.get_by_label("Track and budget expenses").click()
        page.get_by_role("textbox", name="First name").fill(first_name)
        page.get_by_role("textbox", name="Last name").fill(last_name)
        page.get_by_role("button", name="Continue").click()

    expect(page.get_by_test_id("BaseSidebarScreen")).to_be_visible(timeout=10000)


def send_attachment_with_enter_key(page: Page, file_name: str = "file.txt"):
    """
    This function sends an attachment to the user's space chat page.
    """

    file_content = b"This is the content of the file in memory" * 10
    file_object = BytesIO(file_content)


    page.get_by_label("Create").last.click()


    with page.expect_file_chooser() as fc_info:

        page.get_by_label("Add attachment").click()


    file_chooser = fc_info.value
    file_chooser.set_files(
        [
            {
                "name": file_name,  # Set the file name
                "mimeType": "text/plain",  # Set the MIME type
                "buffer": file_object.getvalue(),  # Get the bytes of the in-memory file
            }
        ]
    )


    page.get_by_role("dialog").get_by_role("button", name="Send").wait_for()


    page.keyboard.press("Enter")


def test_focus_on_send_button_in_add_attachment_modal():
    """
    Test to verify that the send button is focused when the modal is opened
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"],
        )
        context = browser.new_context()


        context.tracing.start(screenshots=True, snapshots=True, sources=True)

        try:
            page = context.new_page()
            file_name = f"{int(time.time())}.txt"


            login_user(page, "Asaad", "I")


            send_attachment_with_enter_key(page, file_name)


            expect(page.get_by_label(file_name)).to_be_visible()

            page.wait_for_timeout(3000)
        except Exception:

            raise
        finally:

            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            browser.close()
