import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from utils.trace_cleaner import trace_cleaner
import email
import imaplib
import time

import pytest
from playwright.sync_api import Page, TimeoutError, expect, sync_playwright


EMAIL_USERNAME = "expensifytesting1@gmail.com"
EMAIL_PASSWORD = ""


EMAIL_USERNAME_POSTFIX = "29178.5"


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

@pytest.fixture
def setup_playwright(request):
    width = getattr(request, "param", {}).get("width", 1280)
    height = getattr(request, "param", {}).get("height", 720)

    playwright = sync_playwright().start()

    browser = playwright.chromium.launch(
        headless=True,
        slow_mo=500,
        args=[
            "--ignore-certificate-errors",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
        ],
    )

    context = browser.new_context(viewport={"width": width, "height": height})
    page = context.new_page()

    yield page


    browser.close()
    playwright.stop()


def login_user(page: Page, email: str, first_name: str, last_name: str):

    clear_inbox(EMAIL_USERNAME, EMAIL_PASSWORD)

    page.goto("https://dev.new.expensify.com:8082/")

    page.get_by_test_id("username").fill(email)
    page.get_by_role("button", name="Continue").click()

    try:
        expect(page.get_by_test_id("SignInPage").get_by_test_id("validateCode")).to_be_visible(timeout=5000)
    except (AssertionError, TimeoutError):

        page.get_by_test_id("SignInPage").get_by_role("button", name="Join").click()
    else:

        otp_code = get_otp_from_email(EMAIL_USERNAME, EMAIL_PASSWORD)
        page.get_by_test_id("SignInPage").get_by_test_id("validateCode").fill(otp_code)
        try:
            page.get_by_test_id("SignInPage").get_by_role("button", name="Sign in").click(timeout=2000)
        except (AssertionError, TimeoutError):
            pass

    try:
        expect(page.get_by_text("What do you want to do today?")).to_be_visible(timeout=5000)
    except (AssertionError, TimeoutError):
        pass
    else:

        page.get_by_label("Track and budget expenses").click()
        page.get_by_role("textbox", name="First name").fill(first_name)
        page.get_by_role("textbox", name="Last name").fill(last_name)
        page.get_by_role("button", name="Continue").click()

    expect(page.get_by_test_id("BaseSidebarScreen")).to_be_visible(timeout=10000)


def create_workspace(page: Page):
    def get_existing_workspaces_names():
        return [
            item.split("\n")[0].strip()
            for item in page.get_by_test_id("WorkspacesListPage").get_by_label("row", exact=True).all_inner_texts()
        ]

    page.get_by_role("button", name="My Settings").click()
    page.get_by_role("menuitem", name="Workspaces").click()

    existing_workspaces = get_existing_workspaces_names()
    if existing_workspaces:
        page.get_by_role("button", name="Inbox").click()
        return existing_workspaces[0]

    page.get_by_test_id("WorkspacesListPage").get_by_role("button", name="New workspace").first.click()
    page.locator('button[aria-label="Back"]').nth(0).click()
    existing_workspaces = get_existing_workspaces_names()
    page.get_by_role("button", name="Inbox").click()
    return existing_workspaces[0]


def browse_to_workspace(page: Page, workspace_name: str):
    page.locator('button[aria-label="Workspaces"]').click()
    try:
        page.locator(f'button[aria-label="{workspace_name}"]').click()
    except Exception:
        page.locator(f'button[aria-label="{workspace_name}"]').nth(1).click()
    page.locator('button[aria-label="Navigates to a chat"]', has_text=workspace_name).nth(0).click()


def split_expense_in_workspace(page: Page, amount: int):
    page.locator('button[aria-label="Create"]').last.click()
    page.locator('div[aria-label="Split expense"]').click()
    page.locator('button[aria-label="Manual"]').last.click()
    page.locator('input[role="presentation"]').fill(str(amount))
    page.locator('button[data-listener="Enter"]', has_text="Next").first.click()
    page.locator('button[aria-label="Show more"]').click()
    page.locator('div[data-tag="pressable"]', has_text="Category").click()
    page.locator('button[aria-label="Advertising"]').first.click()
    page.locator('div[data-tag="pressable"]', has_text="Merchant").click()
    page.locator('input[aria-label="Merchant"]').fill("abc")
    page.locator('button[data-listener="Enter"]').last.click()
    page.locator('button[data-listener="Enter"]').last.click()

@pytest.mark.parametrize(
    "setup_playwright",
    [{"width": 1280, "height": 720}],
    indirect=True,
)
def test(setup_playwright):
    trace_path = "/app/expensify/user_tool/output_browser1.zip"
    page = setup_playwright


    page.context.tracing.start(screenshots=True, snapshots=True, sources=True)

    try:
        email = generate_user_email()
        first_name, last_name = "First", "Last"

        login_user(page, email, first_name, last_name)


        workspace_name = create_workspace(page)
        browse_to_workspace(page, workspace_name)
        split_expense_in_workspace(page, 1000)


        page.locator('div[aria-label="Split"]').last.click()
        page.locator('button[aria-label="Show more"]').click()
        split_expense_text = page.locator('div[data-testid="selection-list"]').inner_text()

        assert "Category" in split_expense_text
    except Exception as e:
        raise e
    finally:

        page.context.tracing.stop(path=trace_path)
        trace_cleaner(trace_path)
