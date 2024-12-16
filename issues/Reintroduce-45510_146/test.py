import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright._impl._page import Page
from playwright.sync_api import sync_playwright, expect
import pytest

# Constants for URLs and credentials
NEWDOT_URL = "https://dev.new.expensify.com:8082/"
EMAIL = "ikhanle001+4@gmail.com"


# Login helper function
def new_dot_login(page, email):
    page.goto(NEWDOT_URL)
    page.locator('input[type="email"]').fill(email)
    page.wait_for_timeout(2000)
    page.get_by_role("button", name="Continue").nth(0).click()
    page.wait_for_timeout(10000)
    otp = '435725'
    page.locator('input[data-testid="validateCode"]').fill(otp)


@pytest.fixture(scope="module")
def setup_browser():
    """Initialize browser and page context for all tests within a single session."""
    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="chrome",
            headless=True,
            args=[
                "--ignore-certificate-errors",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process"
            ],
            proxy={"server": "http://localhost:8080"},
            slow_mo=1000
        )
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        yield page
        browser.close()


@pytest.fixture(scope="module")
def login_to_new_dot(setup_browser):
    """Log into the Expensify application with the provided email."""
    page = setup_browser
    new_dot_login(page, EMAIL)
    return page


def reproduce_scenario(page: Page) -> None:
    # Step 1: Create workspace
    page.click('//button[@aria-label="My settings"]')
    page.click('//div[@aria-label="Workspaces"]')
    page.click('//button[@aria-label="New workspace"]')

    # Step 2: Open member page
    member_button = page.get_by_text("Members")
    member_button.click()

    invite_button = page.get_by_role("button", name="Invite member")
    invite_button.click()

    # Step 3: Fill member information and store to random_mail
    random_mail = "example@gmail.com"
    page.get_by_test_id("selection-list-text-input").click()
    page.get_by_test_id("selection-list-text-input").fill(random_mail)
    page.wait_for_timeout(500)

    # Step 4: Invite member
    invited_member_button = page.get_by_role("button", name=random_mail).first
    invited_member_button.click()

    next_button = page.get_by_role("button", name="Next")
    next_button.click()

    page.get_by_test_id("WorkspaceInviteMessagePage").get_by_role("button", name="Invite").click()
    page.wait_for_timeout(2000)

    # Step 5: Invite member
    element = page.get_by_text(random_mail).last
    element.click()

    # Step 6: Open remove from workspace tab
    page.get_by_role("button", name="Remove from workspace").click()

    # Verify the pop up message
    popup_message = page.get_by_text(f"{random_mail} is an approver in this workspace")
    expect(popup_message).not_to_be_visible()


def test_popup_message_on_removing_member_from_ws(login_to_new_dot) -> None:
    page = login_to_new_dot
    page.wait_for_timeout(5000)
    
    # Step 3: Reproduce scenario
    reproduce_scenario(page)

    page.wait_for_timeout(1000)
