import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import email
import imaplib
import time

from playwright._impl._browser import Browser
from playwright._impl._page import Page
from playwright.sync_api import TimeoutError, expect, sync_playwright
from playwright.sync_api._context_manager import PlaywrightContextManager

# Email login credentials
EMAIL_USERNAME = "expensifytesting1@gmail.com"
EMAIL_PASSWORD = "redx tbmr hzpc rbzr"

# Email username postfix
EMAIL_USERNAME_POSTFIX = "41848"


def generate_user_email(user_id=None):
    """
    Generate an email address for a user login.
    """
    temp = EMAIL_USERNAME.rsplit("@", 1)
    username = temp[0].strip()
    domain = temp[1].strip()
    return f"{username}+{EMAIL_USERNAME_POSTFIX}{user_id or ''}@{domain}"


def clear_inbox(username, password):
    """
    Delete all the messages from the Inbox.
    """
    # No need to clear the inbox while replaying
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
    # Return any value while replaying
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


def login_user(context, first_name="Milan", last_name="T") -> tuple[Page, str]:
    """
    Create a new page from the provided context and log in.
    """
    page: Page = context.new_page()
    user_email = generate_user_email()

    # Step 1: Open expensify url
    page.goto("https://dev.new.expensify.com:8082/")

    # Step 2: Login user
    clear_inbox(EMAIL_USERNAME, EMAIL_PASSWORD)
    page.get_by_test_id("username").fill(user_email)
    page.get_by_role("button", name="Continue").click()

    # Step 3: Check if OTP is required for the login
    try:
        expect(page.get_by_test_id("SignInPage").get_by_test_id("validateCode")).to_be_visible(timeout=5000)
    except (AssertionError, TimeoutError):
        # If not required, expect the join button to appear and click the button
        page.get_by_test_id("SignInPage").get_by_role("button", name="Join").click()
    else:
        # Get the OTP and complete verification
        otp_code = get_otp_from_email(EMAIL_USERNAME, EMAIL_PASSWORD)
        page.get_by_test_id("SignInPage").get_by_test_id("validateCode").fill(otp_code)
        try:
            page.get_by_test_id("SignInPage").get_by_role("button", name="Sign in").click(timeout=2000)
        except (AssertionError, TimeoutError):
            pass

    # Step 4: Check if onboarding is required
    try:
        expect(page.get_by_text("What do you want to do today?")).to_be_visible(timeout=5000)
    except (AssertionError, TimeoutError):
        pass
    else:
        # Complete the onboarding
        page.get_by_label("Track and budget expenses").click()
        page.get_by_role("textbox", name="First name").fill(first_name)
        page.get_by_role("textbox", name="Last name").fill(last_name)
        page.get_by_role("button", name="Continue").click()

    # Step 5: Expect the main screen to appear
    expect(page.get_by_test_id("BaseSidebarScreen")).to_be_visible(timeout=10000)

    # Step 6: Dismiss the "Get started here!" tool tip, if shown
    try:
        page.get_by_role("button", name="Close").click(timeout=2000)
    except (AssertionError, TimeoutError):
        pass

    return page, user_email


def test_book_a_call() -> None:
    from utils.trace_cleaner import trace_cleaner

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"],
        )
        context = browser.new_context()

        # Start tracing
        context.tracing.start(screenshots=True, snapshots=True)

        page = None
        try:
            # Step 1: Login user
            page, user_email = login_user(context, "Freek", "Boomer")

            # Continue with the test
            page.get_by_label("Start chat (Floating action)").click()
            page.get_by_label("Start chat", exact=True).click()
            page.get_by_test_id("selection-list-text-input").fill("giodiroes+123@email.com")
            page.wait_for_timeout(1000)
            page.get_by_role("button", name="Add to group").click()
            page.get_by_test_id("selection-list-text-input").fill("universaleu+243@email.com")
            page.wait_for_timeout(1000)
            page.get_by_role("button", name="Add to group").click()
            page.get_by_role("button", name="Next").click()
            page.get_by_role("button", name="Start group").click()
            page.get_by_role("button", name="Create").click()
            page.get_by_label("Split expense").click()
            page.get_by_role("button", name="Select a currency").click()
            page.get_by_test_id("IOURequestStepCurrency").get_by_role("textbox").fill("USD")
            page.get_by_test_id("IOURequestStepCurrency").get_by_role("button", name="USD - $").click()
            page.get_by_placeholder("0").fill("3")
            page.get_by_role("button", name="Next").click()
            page.get_by_role("button", name="Split", exact=False).press("Enter")

            enter_expense = page.get_by_text("Your split $1.00")
            assert enter_expense.is_visible(), "Enter did not save the expense"

            page.get_by_role("button", name="Create").click()
            page.get_by_label("Split expense").click()
            page.get_by_role("button", name="Select a currency").click()
            page.get_by_test_id("IOURequestStepCurrency").get_by_role("textbox").fill("USD")
            page.get_by_test_id("IOURequestStepCurrency").get_by_role("button", name="USD - $").click()
            page.get_by_placeholder("0").fill("12")
            page.get_by_role("button", name="Next").click()
            page.get_by_role("button", name="Split", exact=False).press("ControlOrMeta+Enter")

            ctrl_enter_expense = page.get_by_text("Your split $4.00")
            assert ctrl_enter_expense.is_visible(), "Ctrl+Enter or CMD+Enter did not save the expense"
        except Exception as e:
            # Re-raise after any handling/logging if needed
            raise e
        finally:
            # Stop tracing and clean up
            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")

            # Close the browser
            browser.close()
