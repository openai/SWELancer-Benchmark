from io import BytesIO
import time
from playwright.sync_api import Playwright, BrowserContext, Page, sync_playwright, expect
import pytest
from PIL import Image

from utils.email_handler import EmailHandler


NEWDOT_URL = "https://dev.new.expensify.com:8082/"
EMAIL_ADDRESS = "t56826807@gmail.com"
PASSWORD = "wxck tsaw ocna tkfd"
FIRST_NAME = "D"
LAST_NAME = "C"


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
        channel="chrome",
        headless=False,
        args=[
            "--ignore-certificate-errors",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ],
        proxy={"server": "http://localhost:8080"},
        slow_mo=500,
    )
    context = browser.new_context(
        # viewport={"width": 1280, "height": 680},
    )
    yield context
    browser.close()


@pytest.fixture(scope='function')
def page(context: BrowserContext):
    page = context.new_page()
    yield page
    context.close()


def login_user(page: Page, email: str, password: str, first_name=FIRST_NAME, last_name=LAST_NAME, mock_otp: bool=False):
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

            onboarding_user(page, first_name, last_name)
        else:
            # Await OTP
            otp = "123456" if mock_otp else email_handler.read_otp_code()
            validate_code_input.fill(otp)

            # Wait sign in to complete
            page.get_by_text("Please enter the magic code").wait_for(state="hidden")


def onboarding_user(page: Page, first_name=FIRST_NAME, last_name=LAST_NAME):
    expect(page.get_by_text("What do you want to do today?")).to_be_visible(timeout=30000)
    
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

    if members:
        page.get_by_label("Members").click()
        for member_email in members:
            invite_member(page, member_email)

    if should_go_back:
        page.get_by_label("Back").click()

    return page


def invite_member(ws_setting_members_page: Page, member_email: str):
    ws_setting_members_page.get_by_role("button", name="Invite member").click()
    ws_setting_members_page.get_by_test_id("selection-list-text-input").fill(member_email)
    ws_setting_members_page.get_by_label(member_email).last.click()
    ws_setting_members_page.get_by_role("button", name="Next").click()
    ws_setting_members_page.get_by_test_id("WorkspaceInviteMessagePage").get_by_role("button", name="Invite").click()


def submit_scan_expense(page: Page):
    # Click plus
    page.get_by_label("Create").last.click()
    # Select Submit expense
    page.get_by_label("Submit expense").click()
    # In the Right Hand Modal(RHM) select Scan
    page.get_by_label("Scan").click()

    def create_sample_jpg():
        # Generates an image in memory and returns the bytes
        image = Image.new("RGB", (100, 100), color="blue")
        img_byte_arr = BytesIO()
        image.save(img_byte_arr, format="JPEG")
        img_byte_arr.seek(0)
        return img_byte_arr.getvalue()

    # Choose a file
    with page.expect_file_chooser() as fc_info:
        page.get_by_label("Choose file").click()
        file_chooser = fc_info.value
        file_chooser.set_files(
            {
                "name": "input.jpg",
                "mimeType": "image/jpeg",
                "buffer": create_sample_jpg(),
            }
        )

    # Click Submit expense
    page.get_by_role("button", name="Submit expense").click()


def test(page: Page):
    # Open expensify url
    page.goto(NEWDOT_URL)

    # Login user
    email_address = generate_random_email(seed=1739593958)
    login_user(page, email_address, PASSWORD, FIRST_NAME, LAST_NAME)

    # Enable all beta features
    create_new_workspace(page)

    # Go to the WS chat
    page.get_by_label("Inbox").click()
    display_name = f"{FIRST_NAME} {LAST_NAME}"
    workspace_name = f"{display_name}'s Workspace"
    page.locator(
        'button[aria-label="Navigates to a chat"]',
        has=page.locator('div[data-testid="DisplayNamesWithTooltip"]', has_text=workspace_name)
    ).click()

    # Submit the first scan expense
    submit_scan_expense(page)

    try:
        # Dismiss the pop up ask for loocation permision
        page.get_by_role("button", name="Not Now").click()
    except:
        pass

    # Submit the second scan expense
    submit_scan_expense(page)

    # Verify the user is able to submit back to back scan expenses
    expect(page.get_by_text("Please enter a correct merchant.")).not_to_be_visible(timeout=5000)
