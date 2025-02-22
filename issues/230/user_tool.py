import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import pytest
from playwright.sync_api import sync_playwright, Page
from utils.trace_cleaner import trace_cleaner

SITE_URL = "https://dev.new.expensify.com:8082/"

EMAIL_SUBMITTER = "expensifyolddot+1733902498@gmail.com"
NAME_SUBMITTER = "Sender"

EMAIL_APPROVER_1 = "t56826807+13@gmail.com"
NAME_APPROVER_1 = "Employee"

EMAIL_APPROVER_2 = "expensifyolddot+1733902499@gmail.com"
NAME_APPROVER_2 = "Approver 2"


@pytest.fixture
def setup_playwright():
    playwright = sync_playwright().start()

    browser_user1 = playwright.chromium.launch(
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
    context_args["timezone_id"] = "Asia/Kathmandu"
    context_user1 = browser_user1.new_context(**context_args)
    page_user1 = context_user1.new_page()

    browser_user2 = playwright.chromium.launch(
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
    context_user2 = browser_user2.new_context(**context_args)
    page_user2 = context_user2.new_page()

    yield page_user1, page_user2


    browser_user1.close()
    browser_user2.close()
    playwright.stop()


def login_user(page: Page, email: str):
    page.goto(SITE_URL)
    page.locator('input[type="email"]').fill(email)
    page.locator('button[tabindex="0"]').click()
    try:
        page.locator("button", has_text="Join").click()
    except Exception:
        pass


def complete_onboarding(page: Page, first_name: str, last_name: str = ""):
    page.locator("text='Track and budget expenses'").click()


    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()


def invite_workspace_member(page: Page, member_email: str, member_name: str):
    page.locator('div[aria-label="Members"]').click()
    page.locator("button", has_text="Invite member").click()
    page.locator('input[aria-label="Name, email, or phone number"]').fill(member_email)
    page.locator("button", has_text=member_name).last.click()
    page.locator('button[data-listener="Enter"]', has_text="Next").click()
    page.locator('button[data-listener="Enter"]', has_text="Invite").click()


def browse_to_workspace(page: Page, workspace_name: str):
    page.locator('button[aria-label="Workspaces"]').click()
    try:
        page.locator(f'button[aria-label="{workspace_name}"]').click()
    except Exception:
        page.locator(f'button[aria-label="{workspace_name}"]').nth(1).click()


def browse_to_chat(page: Page, chat_label: str):
    page.locator('button[aria-label="Navigates to a chat"]', has_text=chat_label).nth(
        0
    ).click()


def submit_manual_expense(page: Page, amount: int, merchant: str):
    page.locator('button[aria-label="Create"]').last.click()
    page.locator('div[aria-label="Submit expense"]').click()
    page.locator('button[aria-label="Manual"]').click()
    page.locator('input[placeholder="0"]').fill(str(amount))
    page.locator('button[data-listener="Enter"]', has_text="Next").first.click()
    page.locator('div[role="menuitem"]', has_text="Merchant").click()
    page.locator('input[aria-label="Merchant"]').fill(merchant)
    page.locator('button[data-listener="Enter"]', has_text="Save").click()
    page.locator('button[data-listener="Enter"]', has_text="Submit").click()


def test(setup_playwright):
    page_submitter, page_approver_2 = setup_playwright


    context_user1 = page_submitter.context
    context_user2 = page_approver_2.context
    context_user1.tracing.start(title="trace_user1", screenshots=True, snapshots=True, sources=True)
    context_user2.tracing.start(title="trace_user2", screenshots=True, snapshots=True, sources=True)

    try:
        email_submitter, name_submitter = EMAIL_SUBMITTER, NAME_SUBMITTER
        email_approver_1, name_approver_1 = EMAIL_APPROVER_1, NAME_APPROVER_1
        email_approver_2, name_approver_2 = EMAIL_APPROVER_2, NAME_APPROVER_2

        login_user(page_submitter, email_submitter)
        login_user(page_approver_2, email_approver_2)

        complete_onboarding(page_submitter, name_submitter)
        complete_onboarding(page_approver_2, name_approver_2)


        workspace_name = f"{name_submitter}'s Workspace"
        page_submitter.locator('button[aria-label="Workspaces"]').click()
        (
            page_submitter.get_by_test_id("WorkspaceSwitcherPage")
            .get_by_role("button", name="New workspace")
            .click()
        )

        invite_workspace_member(page_submitter, email_approver_1, name_approver_1)
        invite_workspace_member(page_submitter, email_approver_2, name_approver_2)


        page_submitter.locator('div[aria-label="More features"]').click()
        workflows_toggle = page_submitter.locator('button[aria-label="Configure how spend is approved and paid."][role="switch"]')
        if workflows_toggle.get_attribute('aria-checked') == "false":
            workflows_toggle.click()


        page_submitter.locator('div[aria-label="Workflows"]').click()
        approval_toggle = page_submitter.locator('button[aria-label="Require additional approval before authorizing a payment."][role="switch"]')
        if approval_toggle.get_attribute('aria-checked') == "false":
            approval_toggle.click()


        page_submitter.locator('button[aria-label="Add approvals"]').click()
        page_submitter.locator(
            'div[data-tag="pressable"]', has_text="Additional Approver"
        ).click()


        page_submitter.locator("button", has_text="Upgrade").click()
        page_submitter.locator("button", has_text="Got it, thanks").click()


        page_submitter.locator(
            f'div[aria-label="{name_submitter}"]', has_text="Approver"
        ).first.click()
        page_submitter.locator(f'button[aria-label="{name_approver_1}"]').last.click()
        page_submitter.locator(
            'button[data-listener="Enter"]', has_text="Save"
        ).last.click()

        page_submitter.locator(
            'div[data-tag="pressable"]', has_text="Additional Approver"
        ).first.click()
        page_submitter.locator(f'button[aria-label="{name_approver_2}"]').last.click()
        page_submitter.locator(
            'button[data-listener="Enter"]', has_text="Save"
        ).last.click()

        page_submitter.locator(
            'button[data-listener="Enter"]', has_text="Save"
        ).last.click()
        page_submitter.locator('button[aria-label="Back"]').nth(0).click()
        page_submitter.locator('button[aria-label="Back"]').nth(0).click()


        browse_to_workspace(page_submitter, workspace_name)
        browse_to_chat(page_submitter, workspace_name)
        submit_manual_expense(page_submitter, 10, "abc")


        page_approver_2.wait_for_timeout(2000)
        page_approver_2.goto("https://dev.new.expensify.com:8082/settings/workspaces")
        page_approver_2.get_by_label("Inbox").click()

        browse_to_workspace(page_approver_2, workspace_name)
        browse_to_chat(page_approver_2, f"{workspace_name} owes")
        expense_text = page_approver_2.locator(
            'button[aria-label="View details"]'
        ).last.inner_text()

        assert "Submit" not in expense_text

    finally:

        context_user1.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
        trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
        context_user2.tracing.stop(path="/app/expensify/user_tool/output_browser2.zip")
        trace_cleaner("/app/expensify/user_tool/output_browser2.zip")
