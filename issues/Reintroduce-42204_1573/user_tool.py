import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

"""
Test for the issue: https://github.com/Expensify/App/issues/42204
"""

import email
import imaplib
import logging
import sys
import time

from playwright.sync_api import TimeoutError, expect, sync_playwright
from utils.trace_cleaner import trace_cleaner

# Expensify app URL
EXPENSIFY_URL = "https://dev.new.expensify.com:8082/"

# Email login credentials
EMAIL_USERNAME = "expensifytesting1@gmail.com"
EMAIL_PASSWORD = "redx tbmr hzpc rbzr"

# Email username postfix
EMAIL_USERNAME_POSTFIX = "42212"

# Logger
logging.basicConfig(level=logging.INFO, stream=sys.stdout, format="%(message)s")
LOGGER = logging.getLogger(__name__)


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
    LOGGER.info("Deleting all the messages from the email inbox")
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

    LOGGER.info("Checking the OTP email")
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
                            LOGGER.info("Got the OTP %s", otp_code)
                            return otp_code
            time.sleep(delay)
        imap.close()
    raise AssertionError("Failed to read the OTP from the email")


def launch_browser(pw, headless=True, device=None, geolocation=None):
    """
    Launch the browser.
    """
    browser = pw.chromium.launch(
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
    context_args = {}
    if device:
        context_args.update(pw.devices[device])
    if geolocation:
        context_args["geolocation"] = geolocation
        context_args["permissions"] = ["geolocation"]
    context = browser.new_context(**context_args)
    page = context.new_page()
    return browser, context, page


def login_user(page, email, first_name="John", last_name="Doe"):
    """
    Log into the Expensify app.
    """
    # Clear the email inbox
    clear_inbox(EMAIL_USERNAME, EMAIL_PASSWORD)
    # Open the Expensify app
    page.goto(EXPENSIFY_URL)
    # Login user
    page.get_by_test_id("username").fill(email)
    page.get_by_role("button", name="Continue").click()
    # Check if OTP is required for the login
    try:
        expect(page.get_by_test_id("SignInPage").get_by_test_id("validateCode")).to_be_visible(timeout=5000)
    except AssertionError:
        # If not required, expect the join button to appear and click the button
        page.get_by_test_id("SignInPage").get_by_role("button", name="Join").click()
    else:
        # Get the OTP and complete verification
        # otp_code = get_otp_from_email(EMAIL_USERNAME, EMAIL_PASSWORD)
        page.wait_for_timeout(2000)
        otp_code = "123456"
        page.get_by_test_id("SignInPage").get_by_test_id("validateCode").fill(otp_code)
        # page.get_by_test_id("SignInPage").get_by_role("button", name="Sign in").click()
    # Check if onboarding is required
    try:
        expect(page.get_by_text("What do you want to do today?")).to_be_visible(timeout=10000)
    except AssertionError:
        pass
    else:
        # Complete the onboarding
        page.get_by_label("Track and budget expenses").click()
        page.get_by_role("textbox", name="First name").fill(first_name)
        page.get_by_role("textbox", name="Last name").fill(last_name)
        page.get_by_role("button", name="Continue").click()
        # Exit the Concierge chat, if opened by default
        try:
            expect(page.get_by_role("button", name="Back").first).to_be_visible(timeout=3000)
        except (AssertionError, TimeoutError):
            pass
    # Dismiss the "Get started here!" tool tip, if shown
    try:
        page.get_by_role("button", name="Close").first.click()
    except (AssertionError, TimeoutError):
        pass
    # Expect the main screen to appear
    expect(page.get_by_test_id("BaseSidebarScreen")).to_be_visible(timeout=10000)


def test_warning_is_shown_when_last_member_leaves_the_group():
    """
    Verify that a warning message is shown when the last member from a group opts to leave.
    """
    with sync_playwright() as pw:
        browser, context, page = launch_browser(pw, headless=True, device="Pixel 7")
        # Start tracing
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        trace_path = "/app/expensify/user_tool/output_browser1.zip"
        try:
            # Simultaneously login 2 users
            users = []
            for i in range(1, 3):
                email_address = generate_user_email(user_id=i)
                LOGGER.info("User %s email: %s", i, email_address)
                first_name = f"Fname{i}"
                last_name = f"Lname{i}"
                users.append(
                    {
                        "email": email_address,
                        "first_name": first_name,
                        "last_name": last_name,
                    }
                )

            # Login user 1
            login_user(page, users[0]["email"], first_name=users[0]["first_name"], last_name=users[0]['last_name'])
            LOGGER.info("User logged in successfully")

            # User 1: Leave any existing group chats
            LOGGER.info("User 1: Leave any existing group chats")
            chat_names = (
                page.get_by_test_id("BaseSidebarScreen")
                .get_by_role("button", name="Navigates to a chat")
                .get_by_test_id("DisplayNamesWithTooltip")
                .all_inner_texts()
            )
            chat_names = [chat_name for chat_name in chat_names if f"{users[0]['first_name']}," in chat_name]
            for chat_name in chat_names:
                page.get_by_test_id("BaseSidebarScreen").get_by_role("button", name="Navigates to a chat").get_by_text(
                    chat_name, exact=True
                ).click()
                page.get_by_role("button", name=chat_name).click()
                page.get_by_test_id("ReportDetailsPage").get_by_role("menuitem", name="Leave").click()
                try:
                    page.get_by_role("button", name="Back").first.click(timeout=3000)
                except AssertionError:
                    pass

            # Create a new group chat
            LOGGER.info("User 1: Create a new group chat with user 2")
            page.get_by_role("button", name="Start chat (Floating action)").click()
            page.get_by_role("menuitem", name="Start chat").click()
            page.get_by_test_id("NewChatPage").get_by_test_id("selection-list-text-input").fill(users[1]["email"])
            expect(page.get_by_test_id("NewChatPage").get_by_text(users[1]["email"]).first).to_be_visible()
            page.get_by_test_id("NewChatPage").get_by_role("button", name="Add to group").click()
            page.get_by_test_id("NewChatPage").get_by_role("button", name="Next").click()
            page.get_by_test_id("NewChatConfirmPage").get_by_role("button", name="Start group").click()
            group_name = ", ".join(user["first_name"] for user in users)

            # Remove a member from the group
            LOGGER.info("User 1: Remove user 2 from the group")
            page.get_by_role("button", name=group_name).click()
            page.get_by_test_id("ReportDetailsPage").get_by_role("menuitem", name="Members").click()
            page.get_by_test_id("ReportParticipantsPage").get_by_text(users[1]["first_name"]).click()
            page.get_by_test_id("ReportParticipantDetails").get_by_text("Remove from group", exact=True).click()
            page.get_by_role("button", name="Remove", exact=True).click()
            page.get_by_test_id("ReportParticipantsPage").get_by_role("button", name="Back").click()

            # Try to leave the group
            LOGGER.info("User 1: Try to leave the group")
            page.get_by_test_id("ReportDetailsPage").get_by_role("menuitem", name="Leave").click()

            # Add some delay to make the app state visible to the user running the test
            page.wait_for_timeout(3000)

            # Verify that a warning message is shown
            LOGGER.info("Verify that a warning message is shown to user 1")
            assert_message = "A warning message should appear when the last member tries to leave the group"
            expect(page.get_by_text("Heads up!", exact=True), assert_message).to_be_visible(timeout=3000)

        except Exception as e:
            LOGGER.error("Test encountered an exception: %s", e)
            raise
        finally:
            # Stop and export trace even if test fails
            context.tracing.stop()
            context.tracing.export(path=trace_path)
            trace_cleaner(trace_path)
            context.close()
            browser.close()
