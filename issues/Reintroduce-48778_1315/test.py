import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager

USER_A_EMAIL = "expensify66+1545448765454354421@gmail.com"
USER_A_NAME = "Asaad"
USER_A_LAST_NAME = "I"

APPROVER_B_EMAIL = "expensify66+2855496545438765565424@gmail.com"
APPROVER_B_NAME = "Asaad"
APPROVER_B_LAST_NAME = "J"

APPROVER_C_EMAIL = "expensify66+545487655654343466532@gmail.com"
APPROVER_C_NAME = "Asaad"
APPROVER_C_LAST_NAME = "K"


def login_user(
    page,
    first_name,
    last_name,
    email,
):
    # Step 1: Open expensify url
    page.goto("https://dev.new.expensify.com:8082/")

    page.get_by_test_id("username").fill(email)
    page.get_by_role("button", name="Continue").click()

    page.get_by_role("button", name="Join").click(timeout=3000)

    onboarding_screen = page.locator("text=What do you want to do today?")

    try:
        onboarding_screen.wait_for(timeout=5000)
        # Step 4: Select 'Something else' in onobarding page and click Continue
        page.locator('div[aria-label="Something else"]').click()

        # Step 5: Enter first name, last name and click continue
        page.locator('input[name="fname"]').fill(first_name)
        page.locator('input[name="lname"]').fill(last_name)
        page.get_by_role("button", name="Continue").last.click()
    except:
        pass


def get_context(p: PlaywrightContextManager, browser, is_phone_setup=False):
    # Define browser context options
    context_options = {
        "permissions": ["clipboard-read", "clipboard-write"],
        "reduced_motion": "no-preference",
    }

    if is_phone_setup:
        context_options.update(p.devices["iPhone 12 Pro"])

    # Create a normal browser context
    context = browser.new_context(**context_options)

    # Open a new page
    page = context.new_page()

    return context, page


def create_workspace_and_submit_expense(page):
    page.get_by_label("My settings").click()
    page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").get_by_text(
        "Workspaces"
    ).click()
    page.get_by_label("New workspace").first.click()
    page.get_by_text("Members").click()
    page.get_by_role("button", name="Invite member").click()
    page.get_by_test_id("selection-list-text-input").fill(APPROVER_B_EMAIL)
    page.get_by_test_id("WorkspaceInvitePage").get_by_label(
        APPROVER_B_NAME + " " + APPROVER_B_LAST_NAME
    ).first.click()
    page.get_by_test_id("selection-list-text-input").fill(APPROVER_C_EMAIL)
    page.get_by_test_id("WorkspaceInvitePage").get_by_label(
        APPROVER_C_NAME + " " + APPROVER_C_LAST_NAME
    ).first.click()
    page.get_by_role("button", name="Next").click()
    page.get_by_test_id("WorkspaceInviteMessagePage").get_by_role(
        "button", name="Invite"
    ).click()
    page.get_by_text("More features").click()
    page.get_by_label("Configure how spend is").click()
    page.get_by_test_id("WorkspaceInitialPage").get_by_text("Workflows").click()
    page.get_by_label("Delay expense submissions").click()
    page.get_by_label("Require additional approval").click()
    page.get_by_label("Add approvals").click()
    page.get_by_test_id("WorkspaceWorkflowsApprovalsEditPage").get_by_text(
        "Approver", exact=True
    ).click()
    page.get_by_test_id("WorkspaceWorkflowsApprovalsApproverPage").get_by_label(
        APPROVER_B_NAME + " " + APPROVER_B_LAST_NAME
    ).click()
    page.get_by_role("button", name="Save").click()
    page.get_by_text("Additional approver").click()
    page.get_by_role("button", name="Upgrade").click()
    page.get_by_role("button", name="Got it, thanks").click()
    page.get_by_text("Additional approver").nth(0).click()
    page.get_by_test_id("WorkspaceWorkflowsApprovalsApproverPage").get_by_label(
        APPROVER_C_NAME + " " + APPROVER_C_LAST_NAME
    ).click()
    page.get_by_role("button", name="Save").click()
    page.get_by_text("First approver").click()
    page.get_by_test_id("WorkspaceWorkflowsApprovalsApproverPage").get_by_label(
        APPROVER_B_NAME + " " + APPROVER_B_LAST_NAME
    ).click()
    page.get_by_role("button", name="Save").click()
    page.get_by_role("button", name="Save").click()
    page.get_by_label("Back").nth(0).click()
    workspace_name = page.get_by_label("row").first.text_content().split(".default-")[0]
    page.get_by_label("Inbox").click()
    page.get_by_label("Navigates to a chat").get_by_text(
        workspace_name, exact=True
    ).click()
    page.get_by_label("Create").nth(1).click()
    page.get_by_text("Submit expense", exact=True).click()
    page.get_by_label("Manual").click()
    page.get_by_label("Select a currency").click()
    page.get_by_test_id("selection-list-text-input").fill("usd")
    page.get_by_label("USD - $").click()
    page.get_by_placeholder("0").fill("100")
    page.locator("#numPadContainerView").get_by_role("button", name="Next").click()
    page.get_by_text("Merchant").click()
    page.get_by_role("textbox", name="Merchant").fill("Test")
    page.get_by_role("button", name="Save").click()
    page.get_by_role("button", name="Submit $").click()
    page.get_by_label("View details").wait_for()
    if page.get_by_role("button", name="Submit").is_visible():
        page.get_by_role("button", name="Submit").click()
    return workspace_name


def check_submit(page, workspace_name):
    page.get_by_label("Workspaces").click()
    page.reload()
    page.get_by_test_id("WorkspaceSwitcherPage").get_by_label(workspace_name).click()
    page.get_by_label("Navigates to a chat").get_by_text(
        "#announce", exact=True
    ).wait_for()
    page.get_by_label("Navigates to a chat").get_by_text(
        USER_A_NAME + " " + USER_A_LAST_NAME, exact=True
    ).click()
    page.get_by_label("View details").wait_for()
    expect(
        page.get_by_role("button", name="Submit"),
        "Submit button should not be visible to an approver",
    ).to_have_count(0)


def test_2nd_level_approval_of_submit_expense():
    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True,
            args=[
                "--ignore-certificate-errors",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
            ],
            slow_mo=1000,
        )
        context_a, page_a = get_context(p, browser)
        login_user(page_a, USER_A_NAME, USER_A_LAST_NAME, USER_A_EMAIL)

        context_b, page_b = get_context(p, browser)
        login_user(page_b, APPROVER_B_NAME, APPROVER_B_LAST_NAME, APPROVER_B_EMAIL)
        context_c, page_c = get_context(p, browser)
        login_user(page_c, APPROVER_C_NAME, APPROVER_C_LAST_NAME, APPROVER_C_EMAIL)
        page_a.bring_to_front()
        workspace_name = create_workspace_and_submit_expense(page_a)
        page_c.bring_to_front()
        check_submit(page_c, workspace_name)

        page_a.close()
        context_a.close()
        page_b.close()
        context_b.close()
        page_c.close()
        context_c.close()
        browser.close()