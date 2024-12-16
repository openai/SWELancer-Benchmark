import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from playwright._impl._page import Page
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page
from utils.trace_cleaner import trace_cleaner

#### CONFIG

TEST_URL = "https://dev.new.expensify.com:8082/" # TODO Use the URL that works in your local development
USER_NAME = "expensify31" # TODO Change this to your Gmail username
USER_PASSWORD = "Pass@123456" # TODO Change this to your password

def create_new_workspace_if_not_exists(page: Page):
    """
    Create a new workspace if it does not exist otherwise return the existing one
    """

    page.bring_to_front()

    # Step 1: Navigate to Workspaces settings page
    page.get_by_label("My settings").click()
    page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()
    page.get_by_label("New workspace").last.wait_for()

    # Step 2: Create a new workspace if it does not exist
    if page.get_by_label("row").count() == 0:
        page.get_by_label("New workspace").last.click()
        page.get_by_label("Back").click()

    # Step 3: Get the workspace name
    row_content = page.get_by_label("row").first.text_content()
    workspace_name = row_content.split(".default-", 1)[0]

    # Step 4: Navigate back to inbox
    page.get_by_label("Inbox", exact=True).click()

    return workspace_name


def enable_rules_workflows_and_categories_in_workspace(page: Page, workspace: str):
    """
    Enable rules, workflows and categories in the workspace
    """

    # Step 1: Navigate to workspace settings page
    page.get_by_label("My settings").click()
    page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()
    page.get_by_role("button", name="row").get_by_text(workspace).click()

    # Step 3: Navigate to More features page and enable required features
    page.get_by_label("More features").click()
    if not page.get_by_label("Configure when receipts are").is_checked():
        page.get_by_label("Configure when receipts are").click()
        page.get_by_role("button", name="Upgrade").click()
        page.get_by_role("button", name="Got it, thanks").click()
    if not page.get_by_label("Track and organize spend.").is_checked():
        page.get_by_label("Track and organize spend.").click()
    if not page.get_by_label("Configure how spend is").is_checked():
        page.get_by_label("Configure how spend is").click()
    # Step 4: Navigate to Workflows page and enable require additional approval
    page.get_by_label("Workflows").click()
    if not page.get_by_label("Require additional approval").is_checked():
        page.get_by_label("Require additional approval").click()

    # Step 5: Navigate back to inbox
    page.get_by_test_id("WorkspaceInitialPage").get_by_label("Back").click()
    page.get_by_label("Inbox").click()


def get_test_user_info(seed = None):
    if seed is None:
        return {"email": f"{USER_NAME}@gmail.com", "password": USER_PASSWORD, "first_name": f"{USER_NAME}", "last_name": "Test"}
    else:
        return {"email": f"{USER_NAME}+{seed}@gmail.com", "password": USER_PASSWORD, "first_name": f"Test", "last_name": "User"}


def wait(page, for_seconds=1):
    page.wait_for_timeout(for_seconds * 1000)


def login(p: PlaywrightContextManager, user_info, if_phone=False) -> tuple[Browser, Page, PlaywrightContextManager]:
    # Step 1: Input email and click Continue
    permissions = ['clipboard-read', 'clipboard-write']
    browser = p.chromium.launch(headless=True,
                                args =[
            '--ignore-certificate-errors',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
        ])
    if if_phone:
        phone = p.devices['iPhone 12 Pro']
        context = browser.new_context(**phone, permissions=permissions, reduced_motion='no-preference')
    else:
        context = browser.new_context()

    page = context.new_page()

    page.goto(TEST_URL, timeout=120000)

    phone_or_email_input = page.locator('input[type="email"]')
    expect(phone_or_email_input).to_be_visible()
    phone_or_email_input.fill(user_info["email"])

    continue_button = page.locator('button[tabindex="0"]')
    expect(continue_button).to_be_visible()
    continue_button.click()

    # Step 2: Click Join button if the user is new. Or, use Magic Code to sign in if the user is existing.
    wait(page)

    join_button = page.locator('button:has-text("Join")')
    if join_button.count() > 0:
        print("Join button found. This is a new user.")
        join_button.click()
    else:
        print("Join button not found. This is an existing user. Use Magic Code to sign in.")
        magic_code = "123456"
        print(f"Magic code: {magic_code}")

        validate_code_input = page.locator('input[data-testid="validateCode"]')
        expect(validate_code_input).to_be_visible()
        validate_code_input.fill(magic_code)
    return browser, page, context


def verify_approver_name_in_workspace_categories(
    page: Page, workspace: str, user_name: str
):
    """
    Verify that the approver name is correctly displayed in the workspace categories
    """

    # Step 1: Navigate to workspace settings page
    page.get_by_label("My settings").click()
    page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()
    page.get_by_role("button", name="row").get_by_text(workspace).click()

    # Step 2: Navigate to the Advertising category and set the approver name if it is not set
    page.get_by_label("Categories").click()
    page.locator("#Advertising").click()
    page.get_by_text("Approver").wait_for()
    if page.get_by_role("menuitem", name="Approver").is_visible():
        page.get_by_role("menuitem", name="Approver").click()
        page.get_by_test_id("CategoryApproverPage").get_by_label(user_name).click()

    # Step 3: Verify that the approver name is correctly displayed in the workspace categories
    expect(
        page.get_by_role("menuitem", name=user_name),
        "The approver name is not correctly displayed in the workspace categories",
    ).to_have_count(1)
 
def test_approver_name_in_workspace_categories():
    """
    Test that the approver name is correctly displayed in the workspace categories
    """
    with sync_playwright() as p:
        user_info = get_test_user_info(seed=76534345)
        browser, page, context = login(p, user_info, False)

        # Start tracing
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        try:
            # Step 3: Create a new workspace if it does not exist
            workspace_name = create_new_workspace_if_not_exists(page)
            workspace_name = "Expensify31+623422's Workspace"
            # Step 5: Enable rules, workflows and categories in the workspace
            enable_rules_workflows_and_categories_in_workspace(page, workspace_name)

            # Step 6: Verify that the approver name is correctly displayed in the workspace categories
            verify_approver_name_in_workspace_categories(page, workspace_name, "Asaad I")

        except Exception as e:
            # Re-raise after ensuring trace is saved
            raise e
        finally:
            # Stop tracing and clean trace
            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            # close the browser
            browser.close()
