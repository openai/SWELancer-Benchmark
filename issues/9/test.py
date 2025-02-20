import time
import pytest
from playwright.sync_api import sync_playwright, Page


def generate_random_email():
    return "t56826807+1739441022@gmail.com"


@pytest.fixture
def setup_playwright():
    playwright = sync_playwright().start()

    browser = playwright.chromium.launch(
        headless=False,
        args=[
            "--ignore-certificate-errors",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
        ],
        proxy={"server": "http://localhost:8080"},
        slow_mo=500,
    )
    context = browser.new_context()
    page = context.new_page()

    yield page

    # Cleanup: close browsers and stop Playwright
    browser.close()
    playwright.stop()


def login_user(page: Page, email: str):
    page.goto("https://dev.new.expensify.com:8082/")
    page.locator('input[type="email"]').fill(email)
    page.locator("button", has_text="Continue").click()
    page.locator("button", has_text="Join").click()


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


def test(setup_playwright):
    page = setup_playwright

    email_user, name_user = generate_random_email(), "User A"
    email_approver, name_approver = "t56826807+13@gmail.com", "Employee"

    login_user(page, email_user)

    complete_onboarding(page, name_user)

    # Create new workspace
    page.locator('button[aria-label="Workspaces"]').click()
    (
        page.get_by_test_id("WorkspaceSwitcherPage")
        .get_by_role("button", name="New workspace")
        .click()
    )

    invite_workspace_member(page, email_approver, name_approver)

    # Enable Workflows
    page.locator('div[aria-label="More features"]').click()
    page.locator(
        'button[aria-label="Configure how spend is approved and paid."]'
    ).click()

    # Enable Approvals
    page.locator('div[aria-label="Workflows"]').click()
    approvals_button = page.locator(
        'button[aria-label="Require additional approval before authorizing a payment."]'
    )
    if not approvals_button.is_checked():
        approvals_button.click()

    # Modify Approvals
    page.locator('button[aria-label="Add approvals"]').click()
    page.get_by_test_id("WorkspaceWorkflowsApprovalsEditPage").get_by_text(
        "Approver", exact=True
    ).click()
    page.get_by_test_id("WorkspaceWorkflowsApprovalsApproverPage").get_by_label(
        name_approver
    ).click()
    page.get_by_role("button", name="Save").click()
    page.locator('div[data-tag="pressable"]', has_text="Additional Approver").click()

    # Upgrade Account
    page.locator("button", has_text="Upgrade").click()
    page.locator("button", has_text="Got it, thanks").click()

    # Grab the approver field
    approver_field = (
        page.get_by_test_id("WorkspaceWorkflowsApprovalsEditPage")
        .get_by_text("Approver", exact=True)
        .locator("..")
        .first
    )

    assert name_approver in approver_field.inner_text(), (
        "Approver field has been reset after upgrade!"
    )
