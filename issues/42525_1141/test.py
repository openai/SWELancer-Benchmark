import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import email
import imaplib
import logging
import sys
import time

from playwright._impl._browser import Browser
from playwright._impl._page import Page
from playwright.sync_api import TimeoutError, expect, sync_playwright
from playwright.sync_api._context_manager import PlaywrightContextManager

# Email login credentials
EMAIL_USERNAME = "expensifytesting1@gmail.com"
EMAIL_PASSWORD = "redx tbmr hzpc rbzr"

# Email username postfix
EMAIL_USERNAME_POSTFIX = "42525"

# Logger
logging.basicConfig(level=logging.INFO, stream=sys.stdout, format="%(message)s")
LOGGER = logging.getLogger(__name__)


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
    LOGGER.info("Clear email inbox")
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
    # Return any value while replaying from the flow file
    return "123456"
    LOGGER.info("Waiting for the OTP email")
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
                            LOGGER.info("Got the OTP: %s", otp_code)
                            return otp_code
            time.sleep(delay)
        imap.close()
    raise AssertionError("Failed to read the OTP from the email")


def login_user(p: PlaywrightContextManager, first_name="Milan", last_name="T") -> tuple[Browser, Page, str]:
    # Launch chromiun and open new page
    browser = p.chromium.launch(
        headless=True,
        args=["--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"],
    )
    page = browser.new_page()
    user_email = generate_user_email()
    LOGGER.info("User email: %s", user_email)

    # Step 1: Open expensify url
    page.goto("https://dev.new.expensify.com:8082/")

    # Clear the email inbox
    clear_inbox(EMAIL_USERNAME, EMAIL_PASSWORD)

    # Step 2: Enter email and click continue
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()

    # Step 3: Check if OTP is required for the login
    try:
        expect(page.get_by_test_id("SignInPage").get_by_test_id("validateCode")).to_be_visible(timeout=5000)
    except AssertionError:
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

    # Step 4: Complete the onboarding if dialogue appears
    try:
        expect(page.locator("text=What do you want to do today?")).to_be_visible()
    except AssertionError:
        pass
    else:
        # Select 'Track and budget expenses' in onboarding page and click Continue
        page.locator("text='Track and budget expenses'").click()
        page.get_by_role("button", name="Continue").click()

        # Enter first name, last name and click continue
        page.locator('input[name="fname"]').fill(first_name)
        page.locator('input[name="lname"]').fill(last_name)
        page.get_by_role("button", name="Continue").last.click()

    return browser, page, user_email


def submit_expense_in_workspace_chat(
    browser: Browser, page: Page, user_email: str, workspace_name: str, amount: str = "1000"
) -> tuple[Browser, Page, str]:
    # Step 1: Click on workspace chat
    page.get_by_test_id("BaseSidebarScreen").get_by_text(workspace_name, exact=True).last.click()

    # Step 2: Click on "+" icon and click submit expense
    page.locator('button[aria-label="Create"]').last.click()
    page.locator('div[aria-label="Submit expense"]').click()

    # Step 3: Click on "Manual" button and enter amount
    page.locator('button[aria-label="Manual"]').click()
    page.locator('input[role="presentation"]').fill(amount)

    # Step 4: Click on Next button
    page.locator('button[data-listener="Enter"]', has_text="Next").first.click()

    # Step 5: Add merchant details
    page.locator('div[role="menuitem"]', has_text="Merchant").click()
    page.locator('input[aria-label="Merchant"]').fill("Test Merchant")
    page.locator("button", has_text="Save").click()

    # Step 6: Submit the expense
    page.locator('button[data-listener="Enter"]', has_text="Submit").click()


def test_save_description_in_submitted_expense():
    with sync_playwright() as p:
        new_report_title = ""
        # Step 1: Login user
        browser, page, user_email = login_user(p)

        # Workspace name
        workspace_name = "Workspace 42525"

        # Step 2: Open settings and create the workspace if not already exists
        page.get_by_role("button", name="My settings").click()
        page.get_by_role("menuitem", name="Workspaces").click()
        existing_workspaces = [
            item.split("\n")[0].strip()
            for item in page.get_by_test_id("WorkspacesListPage").get_by_label("row", exact=True).all_inner_texts()
        ]
        if workspace_name not in existing_workspaces:
            page.get_by_role("button", name="New workspace").first.click()
            # Set workspace name
            page.get_by_test_id("WorkspacePageWithSections").get_by_text("Name", exact=True).click()
            page.get_by_test_id("WorkspaceNamePage").get_by_role("textbox").fill(workspace_name)
            page.get_by_test_id("WorkspaceNamePage").get_by_role("button", name="Save").click()
            LOGGER.info("Created workspace '%s'", workspace_name)
            # Go back
            page.locator('button[aria-label="Back"]').click()
        else:
            LOGGER.info("Workspace '%s' already exists", workspace_name)
        page.wait_for_timeout(2000)

        # Step 3: Click on Back arrow to go back and navigate to inbox screen
        page.locator('button[aria-label="Inbox"]').click()

        # Step 4: Submit expenses twice in the workspace chat
        submit_expense_in_workspace_chat(browser, page, user_email, workspace_name)
        submit_expense_in_workspace_chat(browser, page, user_email, workspace_name)
        page.wait_for_timeout(2000)

        # Step 5: Navigate to the chat and view details of the expense report
        page.get_by_test_id("BaseSidebarScreen").get_by_text(workspace_name, exact=True).last.click()
        page.locator('button[aria-label="View details"]').last.click()
        page.locator('button[aria-label^="Expense Report #"]').last.click()
        page.locator('div[aria-label^="Expense Report #"]').click()

        # Step 6: Edit the expense report title and save
        page.locator('input[name="text_title"]').fill(new_report_title)
        page.locator('button[data-listener="Enter"]', has_text="Save").first.click()

        # Step 7: Check if the "This field is required" error appears
        error_field = page.locator("text=This field is required.")
        if error_field.is_visible():
            assert True, "Empty Report title cannot be saved."
        else:
            assert False, "Empty Report title has been saved."

        browser.close()
