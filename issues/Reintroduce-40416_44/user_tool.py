import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright._impl._page import Page
from playwright.sync_api import sync_playwright, expect
from utils.trace_cleaner import trace_cleaner

def sign_in_new_dot(page: Page, email: str):

    page.goto("https://dev.new.expensify.com:8082")
    page.get_by_test_id("username").fill(email)
    page.get_by_role("button", name="Continue").click()
    page.get_by_test_id("validateCode").fill("123456")
    page.get_by_text("Please enter the magic code").wait_for(state="hidden")

def admin_create_workspace_add_member(page: Page, workspace_name, member_email):

    page.get_by_label("My settings").click()
    page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()
    page.get_by_label("New workspace").click()

    page.get_by_test_id("WorkspacePageWithSections").get_by_text("Name").click()
    page.get_by_role("textbox", name="Name").fill(workspace_name)
    page.get_by_role("button", name="Save").click()

    page.get_by_label("Members").click()
    page.get_by_role("button", name="Invite member").click()
    page.get_by_test_id("selection-list-text-input").fill(member_email)

    page.locator("button").filter(has_text=member_email).click()
    page.get_by_role("button", name="Next").click()
    page.get_by_test_id("WorkspaceInviteMessagePage").get_by_role("button", name="Invite").click()

    page.locator("button").filter(has_text=member_email).click()

    page.get_by_role("button", name="Remove from workspace").wait_for()

def member_leave_workspace(page, workspace_name):

    page.get_by_label("My settings").click()
    page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()

    page.locator("button").filter(has_text=workspace_name).get_by_label("More").click()
    page.get_by_label("Leave").click()

def test_run():
    with sync_playwright() as p:

        email_admin = "testexpensifyturing+008@gmail.com"
        email_member = "testexpensifyturing+009@gmail.com"
        workspace_name = "Work_173409955552"

        browser_admin = p.chromium.launch(
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

        context_admin = browser_admin.new_context(timezone_id="Asia/Karachi", ignore_https_errors=True)
        # Start tracing for admin
        context_admin.tracing.start(screenshots=True, snapshots=True)
        page_admin = context_admin.new_page()

        browser_member = p.chromium.launch(
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

        context_member = browser_member.new_context(timezone_id="Asia/Karachi", ignore_https_errors=True)
        # Start tracing for member
        context_member.tracing.start(screenshots=True, snapshots=True)
        page_member = context_member.new_page()

        try:
            sign_in_new_dot(page_admin, email_admin)
            admin_create_workspace_add_member(page_admin, workspace_name, email_member)

            sign_in_new_dot(page_member, email_member)
            member_leave_workspace(page_member, workspace_name)

            page_admin.reload()

            expect(page_admin.locator('button:has-text("Remove from workspace")')).not_to_be_visible()
        except Exception as e:
            print(f"Test failed: {e}")
            raise
        finally:
            # Stop tracing and clean traces for both contexts
            context_admin.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")

            context_member.tracing.stop(path="/app/expensify/user_tool/output_browser2.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser2.zip")

            browser_admin.close()
            browser_member.close()
