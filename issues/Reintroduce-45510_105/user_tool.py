import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright._impl._page import Page
from playwright.sync_api import expect, sync_playwright
from utils.trace_cleaner import trace_cleaner

# Email login credentials
EMAIL_USERNAME = "expensifytesting1@gmail.com"
EMAIL_PASSWORD = "redx tbmr hzpc rbzr"

# Email username postfix
EMAIL_USERNAME_POSTFIX = 6

# User first and last name
FIRST_NAME = "Alice"
LAST_NAME = "Aliceoglu"


def generate_user_email():
    """
    Generate an email address for a user login.
    """
    temp = EMAIL_USERNAME.rsplit("@", 1)
    username = temp[0].strip()
    domain = temp[1].strip()
    return f"{username}+{EMAIL_USERNAME_POSTFIX}@{domain}"


def login_user(page: Page) -> None:
    # Step 1: Enter email and click continue
    username_input = page.get_by_test_id("username")
    username_input.click()

    username_input.fill(generate_user_email())

    continue_button = page.get_by_role("button", name="Continue")
    continue_button.click()

    # Step 2: Click join button
    join_button = page.get_by_role("button", name="Join")
    join_button.click()

    # Step 3: Select 'Track and budget expenses' in onboarding page and click Continue
    track_expenses_text = page.get_by_text("Track and budget expenses")
    track_expenses_text.click()


def enter_user_information(page: Page) -> None:
    # Step 1: Enter first name, last name and click continue
    first_name_input = page.get_by_role("textbox", name="First name")
    first_name_input.fill(FIRST_NAME)

    first_name_input.press("Tab")

    last_name_input = page.get_by_role("textbox", name="Last name")
    last_name_input.fill(LAST_NAME)

    # Step 2: Click continue button
    continue_button_after_names = page.get_by_role("button", name="Continue")
    continue_button_after_names.click()


def reproduce_scenario(page: Page) -> None:
    # Step 1: Create workspace
    start_chat_button = page.get_by_label("Start chat (Floating action)")
    start_chat_button.click()

    new_ws_button = page.get_by_text("New workspace")
    new_ws_button.click()

    # Step 2: Open member page
    member_button = page.get_by_text("Members")
    member_button.click()

    invite_button = page.get_by_role("button", name="Invite member")
    invite_button.click()

    # Step 3: Fill member information and store to random_mail
    random_mail = "testuser@gmail.com"
    page.get_by_test_id("selection-list-text-input").click()
    page.get_by_test_id("selection-list-text-input").fill(random_mail)
    # Step 4: Invite member
    invited_member_button = page.get_by_role("button", name="testuser somasundar").first
    invited_member_button.click()
    next_button = page.get_by_role("button", name="Next")
    next_button.click()

    page.get_by_test_id("WorkspaceInviteMessagePage").get_by_role("button", name="Invite").click()

    # Step 5: Click on the invited member row, retry until the "Remove from workspace" pane is opened

    page.get_by_role("button", name= "testuser").first.click()
    # Step 6: Open remove from workspace tab
    page.get_by_role("button", name="Remove from workspace").last.click()

    # Verify the pop up message
    popup_message = page.get_by_text(f"{random_mail} is an approver in this workspace")
    expect(popup_message).not_to_be_visible()


def test_popup_message_on_removing_member_from_ws() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            slow_mo=1000,
            args=["--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"],
            proxy={"server": "http://localhost:8080"}
        )
        context = browser.new_context(ignore_https_errors=True)
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        page = context.new_page()
        page.goto("https://dev.new.expensify.com:8082/")
        try:
            # Step 1: Login user
            login_user(page)

            # Step 2: Enter User Information
            enter_user_information(page)

            # Step 3: Reproduce scenario
            reproduce_scenario(page)
        finally:
            # Stop trace and clean it
            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            context.tracing.stop(path=trace_path)
            trace_cleaner(trace_path)

        context.close()
        browser.close()
