import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import email
import imaplib
import time

from playwright._impl._page import Page
from playwright.sync_api import TimeoutError, expect, sync_playwright
from utils.trace_cleaner import trace_cleaner

# Email login credentials
EMAIL_USERNAME = "expensifytesting1@gmail.com"
EMAIL_PASSWORD = "redx tbmr hzpc rbzr"

# Email username postfix
EMAIL_USERNAME_POSTFIX = "40464.7"

# User first and last name
FIRST_NAME = "Alice"
LAST_NAME = "Aliceoglu"


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
    # No need to clear inbox while replaying
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


def login_user(page: Page) -> None:
    # Clear the email inbox
    clear_inbox(EMAIL_USERNAME, EMAIL_PASSWORD)
    # Login user
    user_email = generate_user_email()
    page.get_by_test_id("username").fill(user_email)
    page.get_by_role("button", name="Continue").click()
    # Check if OTP is required for the login
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


def enter_user_information(page: Page) -> None:
    # Check if onboarding is required
    try:
        expect(page.get_by_text("What do you want to do today?")).to_be_visible(timeout=5000)
    except (AssertionError, TimeoutError):
        pass
    else:
        # Complete the onboarding
        page.get_by_label("Track and budget expenses").click()
        page.get_by_role("textbox", name="First name").fill(FIRST_NAME)
        page.get_by_role("textbox", name="Last name").fill(LAST_NAME)
        page.get_by_role("button", name="Continue").click()
    # Dismiss the "Get started here!" tool tip, if shown
    try:
        page.get_by_role("button", name="Close").click(timeout=3000)
    except (AssertionError, TimeoutError):
        pass
    # Expect the main screen to appear
    expect(page.get_by_test_id("BaseSidebarScreen")).to_be_visible(timeout=7000)


def reproduce_scenario(page: Page) -> None:
    # Create workspace if not already created
    page.get_by_test_id("CustomBottomTabNavigator").get_by_role("button", name="My settings").click()
    page.get_by_test_id("InitialSettingsPage").get_by_role("menuitem", name="Workspaces").click()
    existing_workspaces = [
        item.split("\n")[0].strip()
        for item in page.get_by_test_id("WorkspacesListPage").get_by_label("row", exact=True).all_inner_texts()
    ]
    workspace_name = "WS Test"
    if workspace_name not in existing_workspaces:
        page.get_by_test_id("WorkspacesListPage").get_by_role("button", name="New workspace").first.click()
        page.wait_for_timeout(1000)
        page.get_by_test_id("WorkspacePageWithSections").get_by_text("Workspace", exact=False).first.click()
        page.get_by_test_id("WorkspaceNamePage").get_by_role("textbox", name="Name").fill(workspace_name)
        page.get_by_test_id("WorkspaceNamePage").get_by_role("button", name="Save").click()
        page.wait_for_timeout(1000)
        page.get_by_test_id("WorkspaceInitialPage").get_by_role("button", name="Back").click()

    page.get_by_label("Inbox").click()
    page.wait_for_timeout(1000)

    page.get_by_test_id("BaseSidebarScreen").get_by_text(workspace_name, exact=True).last.click()

    page.get_by_role("button", name="Create").click()

    page.get_by_role("menuitem", name="Track expense").click()

    page.get_by_label("Manual").click()

    page.get_by_placeholder("0").fill("1000")
    page.get_by_role("button", name="Next").first.click()

    page.get_by_text("Merchant").click()
    page.get_by_role("textbox", name="Merchant").fill("hello")
    page.get_by_role("button", name="Save").click()

    page.get_by_role("button", name="Track expense").click()
    page.get_by_label("View details").last.click()

    page.get_by_label("Expense Report #").last.click()

    # Verify that the report details page open and not the "not here" page
    expect(page.get_by_test_id("ReportDetailsPage").get_by_text("Expense Report #")).to_be_visible()
    expect(page.locator("text=Hmm... it's not here")).not_to_be_visible()


def test_check_expense_title() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            args=["--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"],
        )
        context = browser.new_context(ignore_https_errors=True)
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        try:
            page = context.new_page()
            page.goto("https://127.0.0.1:8082/")

            # Step 1: Login user
            login_user(page)

            # Step 2: Enter User Information
            enter_user_information(page)

            # Step 3: Reproduce scenario
            reproduce_scenario(page)

            page.wait_for_timeout(1000)
        except Exception as e:
            print(f"Test encountered an error: {e}")
            raise
        finally:
            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            context.close()
            browser.close()
