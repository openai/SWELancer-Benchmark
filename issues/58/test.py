import time
from playwright.sync_api import sync_playwright, expect

# Expensify app URL
NEWDOT_URL = "https://dev.new.expensify.com:8082"
OLDDOT_URL = "http://127.0.0.1:9000/"
GMAIL = "biruktassew21@gmail.com"

def generate_new_email(email_address=GMAIL):
        # Add random number suffix to the email before the "@" symbol
        username, domain = email_address.split('@')
        timestamp = int(time.time() * 1_000_000)
        return f"{username}+{timestamp}@{domain}"

def signup_user(page, email, first_name="Test", last_name="User"):
    page.get_by_role("textbox", name="Phone or email").fill(email)
    page.get_by_role("button", name="Continue").click()
    page.get_by_role("button", name="Join").click()

    page.wait_for_selector('text="What do you want to do today?"')
    expect(page.locator("text=What do you want to do today?")).to_be_visible()
    
    page.get_by_label("Track and budget expenses").click()
    page.get_by_role("button", name="Continue").click()

    page.fill('input[name="fname"]', first_name)
    page.fill('input[name="lname"]', last_name)
    page.get_by_role("button", name="Continue").last.click()

    page.wait_for_timeout(2000)

def create_workspace(page):
    # create a workspace and go to its chat
    page.get_by_label("My settings").click()
    page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").get_by_text("Workspaces").click()
    page.get_by_label("New workspace").first.click()
    page.get_by_test_id("WorkspacePageWithSections").get_by_text("Name").click()
    page.get_by_role("textbox", name="Name").press("ControlOrMeta+a")
    page.get_by_role("textbox", name="Name").fill("Test Workspace")
    page.get_by_role("button", name="Save").click()

def test_approver_rule_enforcement():
    with sync_playwright() as pw:
        
        admin = "biruktassew21+1740055289009077@gmail.com"
        expense_from = "biruktassew21+1740055289009080@gmail.com"
        approver = "biruktassew21+1740055289009081@gmail.com"

        # Launch the app
        browser = pw.chromium.launch(
            channel="chrome",
            headless=False,
            args=[
                "--ignore-certificate-errors",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process"
            ],
            proxy={"server": "http://localhost:8080"},
            slow_mo=500
        )

        page = browser.new_page()
        page.goto(NEWDOT_URL)
    
        # signup user
        signup_user(page, admin)

        # Create a workspace
        create_workspace(page)

        # Invite memebrs
        page.get_by_text("Members").click()
        page.get_by_role("button", name="Invite member").click()
        page.get_by_test_id("selection-list-text-input").fill(expense_from)
        page.get_by_test_id("selection-list").get_by_label(expense_from).last.click()
        page.get_by_test_id("selection-list-text-input").fill(approver)
        page.get_by_test_id("selection-list").get_by_label(approver).last.click()
        page.get_by_role("button", name="Next").click()
        page.get_by_test_id("WorkspaceInviteMessagePage").get_by_role("button", name="Invite").click()

        # Enable workflows and rules
        page.get_by_text("More features").click()
        page.get_by_label("Require receipts, flag high").click()

        try:
            page.get_by_test_id("upgrade-button").click(timeout=1000)
            page.get_by_test_id("confirmation-button").click()
        except:
            pass
        try:
            page.get_by_test_id("WorkspaceInitialPage").get_by_text("Workflows").click(timeout=1000)
        except:
             page.get_by_label("Configure how spend is").click()
        
        # Add approver and set prevent-self-approval on
        page.get_by_test_id("WorkspaceInitialPage").get_by_text("Workflows").click()
        page.get_by_test_id("WorkspaceInitialPage").get_by_text("Rules").click()
        page.get_by_label("Prevent self-approvals").click()

        # Add expense-from
        page.get_by_test_id("WorkspaceInitialPage").get_by_text("Workflows").click()
        try:
            page.get_by_text("Add approval workflow").click(timeout=2000)
        except:
            page.get_by_label("Require additional approval").click()
            page.get_by_text("Add approval workflow").click()
        page.get_by_test_id("WorkspaceWorkflowsApprovalsExpensesFromPage").get_by_test_id("selection-list").get_by_label(expense_from).first.click()
        page.get_by_role("button", name="Next").click()

        # Add approver after asseting the member added in expense-from is not present here
        expect(page.get_by_test_id("WorkspaceWorkflowsApprovalsApproverPage").get_by_label(expense_from)).not_to_be_visible()
        page.get_by_test_id("WorkspaceWorkflowsApprovalsApproverPage").get_by_label(approver).click()
        page.get_by_role("button", name="Next").click()

        # Assert the approver in not in the expense-from list
        page.get_by_test_id("WorkspaceWorkflowsApprovalsCreatePage").get_by_text("Expenses from").click()
        expect(page.get_by_role("button", name=approver).first).not_to_be_visible()

        # Close the browser
        browser.close()

