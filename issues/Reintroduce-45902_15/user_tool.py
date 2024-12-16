import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright
from playwright._impl._page import Page

from utils.trace_cleaner import trace_cleaner


def login_user(page: Page, email: str):
    page.goto("https://dev.new.expensify.com:8082/")
    page.locator('input[type="email"]').fill(email)
    page.locator("button", has_text="Continue").click()
    page.locator("button", has_text="Join").click()


def complete_onboarding(page: Page, first_name: str, last_name: str):
    page.locator("text='Track and budget expenses'").click()
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()


def submit_expense(page: Page, amount: int, merchant: str):
    page.locator('button[aria-label="Create"]').last.click()
    page.locator('text="Submit expense"').last.click()
    page.locator('button[aria-label="Manual"]').last.click()
    page.locator('input[role="presentation"]').fill(f"{amount}")
    page.locator('button[data-listener="Enter"]', has_text="Next").first.click()
    page.locator('text="Merchant"').last.click()
    page.locator('input[aria-label="Merchant"]').fill(merchant)
    page.locator('button[data-listener="Enter"]', has_text="Save").first.click()
    page.locator('button[data-listener="Enter"]', has_text="Submit").first.click()


def test_save_description_in_submitted_expense():
    with sync_playwright() as p:
        user1_email = "t56826807+1735044400@gmail.com"
        user2_email = "t56826807+1735044420@gmail.com"

        browser = p.chromium.launch(
            channel="chrome",
            headless=True,
            args=[
                "--ignore-certificate-errors",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
            ],
            proxy={"server": "http://localhost:8080"},
            slow_mo=1000,
        )
        context1 = browser.new_context()
        context2 = browser.new_context()

        # Start tracing in both contexts
        context1.tracing.start(title="context1", snapshots=True, screenshots=True)
        context2.tracing.start(title="context2", snapshots=True, screenshots=True)

        try:
            page1 = context1.new_page()
            page2 = context2.new_page()

            login_user(page1, user1_email)
            login_user(page2, user2_email)

            complete_onboarding(page1, "User", "A")
            complete_onboarding(page2, "User", "B")

            # [User A] Create Workspace
            page1.locator('button[aria-label="Start chat (Floating action)"]').click()
            page1.locator('div[aria-label="New workspace"]').click()

            # [User A] Enable approvals
            page1.locator('text="More features"').last.click()
            page1.locator(
                'button[aria-label="Configure how spend is approved and paid."]'
            ).last.click()
            page1.locator('div[aria-label="Workflows"]').last.click()
            page1.locator(
                'button[aria-label="Require additional approval before authorizing a payment."]'
            ).last.click()

            # [User A] Invite User B
            page1.locator('div[aria-label="Members"]').last.click()
            page1.locator('text="Invite member"').last.click()
            page1.locator('input[aria-label="Name, email, or phone number"]').fill(
                user2_email
            )
            page1.locator('button[aria-label="User B"]').last.click()
            page1.locator('text="Next"').last.click()
            page1.locator('text="Invite"').last.click()

            # [User B] Navigate to workspace
            page2.locator('button[aria-label="Workspaces"]').first.click()
            page2.locator('text="User A\'s Workspace"').last.click()

            # [User B] Submit expenses
            submit_expense(page2, 100, "1")
            submit_expense(page2, 200, "2")

            # [User A] Navigate to submitted expenses
            page1.locator('button[aria-label="Back"]').last.click()
            page1.locator('button[aria-label="Inbox"]').last.click()
            page1.locator('button[aria-label="Workspaces"]').first.click()
            page1.locator('text="User A\'s Workspace"').last.click()
            page1.locator(
                'button[aria-label="Navigates to a chat"]', has_text="User B"
            ).first.click()

            # [User A] Hold one expense
            page1.get_by_role("button", name="View details").last.click()
            page1.locator("div", has_text="100").last.click()
            page1.locator(
                'div[data-testid="DisplayNamesWithTooltip"]', has_text="100"
            ).last.click()
            page1.locator('text="Hold"').last.click()
            hold_reason = "random"
            page1.locator('input[aria-label="Reason"]').fill(hold_reason)
            page1.locator(
                'button[data-listener="Enter"]', has_text="Hold expense"
            ).first.click()
            page1.locator('button[data-listener="Enter"]', has_text="Got it").first.click()
            page1.locator("div", has_text="Expense Report").last.click()

            # [User A] Approve remaining expenses
            page1.locator('text="Approve"').last.click()
            page1.locator("div", has_text="Approve only").last.click()

            # [User B] Confirm if expense report for held expense appears on LHN
            expense_lhn = page2.locator(
                'button[aria-label="Navigates to a chat"]', has_text=hold_reason
            )
            try:
                expense_lhn.wait_for(state="visible", timeout=5000)
                is_expense_lhn_visible = True
            except Exception:
                is_expense_lhn_visible = False

            assert is_expense_lhn_visible

            # [User B] Confirm if held expense report on LHN has circle
            circle = expense_lhn.locator("circle")
            circle_count = circle.count()
            assert circle_count > 0

        finally:
            # Stop tracing and clean traces no matter test outcome
            context1.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            context2.tracing.stop(path="/app/expensify/user_tool/output_browser2.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser2.zip")
