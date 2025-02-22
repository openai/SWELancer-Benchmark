import re
import time
from playwright.sync_api import Playwright, BrowserContext, Page, sync_playwright, expect
import pytest

from utils.email_handler import EmailHandler


NEWDOT_URL = "https://dev.new.expensify.com:8082/"
EMAIL_ADDRESS = "t56826807@gmail.com"
PASSWORD = "wxck tsaw ocna tkfd"
FIRST_NAME = "D"
LAST_NAME = "C"
MOCK_OTP = False


def generate_random_email(base_email=EMAIL_ADDRESS, seed=None):
    if seed is None:
        seed = int(time.time())
    email_user, domain = base_email.split('@')
    return f"{email_user}+{seed}@{domain}"


@pytest.fixture(scope='session')
def playwright_instance():
    with sync_playwright() as playwright:
        yield playwright


@pytest.fixture(scope='session')
def context(playwright_instance: Playwright):
    browser = playwright_instance.chromium.launch(
        proxy = {"server": "http://localhost:8080"}, headless = False, args = ["--no-sandbox", "--disable-dev-shm-usage", "--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"], slow_mo = 500, channel = "chromium")
    context = browser.new_context()
    yield context
    browser.close()


@pytest.fixture(scope='function')
def page(context: BrowserContext):
    page = context.new_page()
    yield page
    context.close()


def login_user(page: Page, email: str, password: str, first_name=FIRST_NAME, last_name=LAST_NAME, mock_otp: bool = MOCK_OTP):
    try:
        # If the user is already logged in, the inbox should be visible
        expect(page.get_by_label("Inbox")).to_be_visible(timeout=3000)
        return
    except:
        pass

    with EmailHandler(email, password) as email_handler:
        # Clean inbox
        if not mock_otp:
            email_handler.mark_all_unread_as_read()

        # Enter email and click continue
        page.get_by_test_id("username").fill(email)
        page.get_by_role("button", name="Continue").click()

        # Check if we have can join directly or we need a magic code
        join_button = page.get_by_role("button", name="Join")
        validate_code_input = page.get_by_test_id("validateCode")
        expect(join_button.or_(validate_code_input)).to_be_visible()

        if (join_button.is_visible()):
            join_button.click()

            try:
                onboarding_user(page, first_name, last_name)
            except:
                pass
        else:
            # Await OTP
            otp = "123456" if mock_otp else email_handler.read_otp_code()
            validate_code_input.fill(otp)

            # Wait sign in to complete
            page.get_by_text("Please enter the magic code").wait_for(state="hidden")


def onboarding_user(page: Page, first_name=FIRST_NAME, last_name=LAST_NAME):
    expect(page.get_by_text("What do you want to do today?")).to_be_visible()
    
    # Select 'Track and budget expenses' in onboarding page and click Continue
    activity_text="Track and budget expenses"
    page.get_by_label(activity_text).click()

    # Enter first name, last name and click continue
    page.get_by_role("textbox", name="First name").fill(first_name)
    page.get_by_role("textbox", name="Last name").fill(last_name)
    page.get_by_role("button", name="Continue").last.click()


def create_new_workspace(
    page: Page,
    name: str = None,
    default_currency: str = None,
    members: list[str] = None,
    enable_distance_rates: bool = False,
    should_go_back: bool = True,
):
    # Click on + icon and click on "New workspace"
    page.get_by_label("Start chat (Floating action)").click()
    page.get_by_label("New workspace").click()

    if name:
        page.get_by_test_id("WorkspacePageWithSections").get_by_text("Name").click()
        page.get_by_role("textbox", name="Name").fill(name)
        page.get_by_role("button", name="Save").click()

    if default_currency:
        page.get_by_text("Default currency").click()
        page.get_by_test_id("selection-list-text-input").fill(default_currency)
        page.get_by_label(default_currency).click()

    try:
        page.get_by_role("button", name="Confirm").click(timeout=2000)
    except:
        pass

    if members:
        page.get_by_label("Members").click()
        for member_email in members:
            invite_member(page, member_email)

    if enable_distance_rates:
        page.get_by_label("More features").click()
        page.get_by_label("Add, update, and enforce").click()
        page.get_by_label("Distance rates").click()

    if should_go_back:
        page.get_by_test_id("WorkspaceInitialPage").get_by_label("Back").click()

    return page


def invite_member(ws_setting_members_page: Page, member_email: str):
    ws_setting_members_page.get_by_role("button", name="Invite member").click()
    ws_setting_members_page.get_by_test_id("selection-list-text-input").fill(member_email)
    ws_setting_members_page.get_by_label(member_email).last.click()
    ws_setting_members_page.get_by_role("button", name="Next").click()
    ws_setting_members_page.get_by_test_id("WorkspaceInviteMessagePage").get_by_role("button", name="Invite").click()


def create_manual_expense(page: Page, amount: int = 123, currency: str = "USD - $", merchant: str = "ABC"):
    page.get_by_label("Create").last.click()
    submit_button = page.get_by_label("Submit expense")
    create_button = page.get_by_label("Create expense")
    (submit_button.or_(create_button)).click()
    page.get_by_label("Manual").click()
    page.get_by_label("Select a currency").click()
    page.get_by_test_id("selection-list-text-input").fill(currency)
    page.get_by_label(currency).click()
    page.get_by_placeholder("0").fill(f"{amount}")
    page.locator("#numPadContainerView").get_by_role("button", name="Next").click()
    page.get_by_role("menuitem", name="Merchant Required").click()
    page.get_by_role("textbox", name="Merchant").fill(merchant)
    page.get_by_role("button", name="Save").click()
    page.get_by_role("button", name="Submit").click()


def test(page: Page):
    # Open expensify url
    page.bring_to_front()
    page.goto(NEWDOT_URL)
    # Login user
    email_address = generate_random_email(seed=1739965578)
    login_user(page, email_address, PASSWORD, mock_otp=True)

    # Create a new workspace (do not set up bank account).
    create_new_workspace(page)

    # Go to workspace chat.
    page.get_by_label("Inbox").click()
    workspace_chat = page.locator(
        'button[aria-label="Navigates to a chat"]',
        has=page.locator('div[data-testid="DisplayNamesWithTooltip"]', has_text=" Workspace")
    )
    workspace_chat.click()
    # Submit an expense.
    create_manual_expense(page)
    # Click on the down caret button on the expense preview in the workspace chat.
    page.get_by_label("View details").get_by_role("button").nth(1).click()
    # Select Pay with Expensify.
    page.get_by_label(re.compile(r"Pay .* with Expensify")).click()
    # Go to Search.
    page.get_by_test_id("CustomBottomTabNavigator").get_by_label("Search").click()
    # Click Pay on the expense item.
    page.get_by_role("button", name="Pay", exact=True).click()
    # Note that it opens expense details RHP.
    expense_details_header = page.get_by_label("Expense Report #").first
    expect(expense_details_header).to_be_visible()
    # Close the RHP.
    page.get_by_label("Back").click()
    # Select the same expense via checkbox.
    page.get_by_test_id("selection-list").get_by_role("checkbox").click()
    # Click on the dropdown.
    page.get_by_role("button", name="selected").click()
    # Click Pay.
    page.get_by_label("Pay").click()
    # Verify Expense detalis RHP will open.
    expect(expense_details_header).to_be_visible()
