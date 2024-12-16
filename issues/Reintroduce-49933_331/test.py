import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

"""
Test for the issue: https://github.com/Expensify/App/issues/49933
"""
import logging
import sys
from playwright.sync_api import Page, Playwright, expect, sync_playwright

# Expensify app URL
EXPENSIFY_URL = "https://dev.new.expensify.com:8082/"

# Email login credentials
EMAIL_USERNAME = "expensifytesting1@gmail.com"

# Email username postfix
EMAIL_USERNAME_POSTFIX = "gcz2dWd"

# Logger
logging.basicConfig(level=logging.INFO, stream=sys.stdout, format="%(message)s")
LOGGER = logging.getLogger(__name__)


def generate_recipient_email(user_id: str = ""):
    """
    Generate an email address for a user login.
    """
    temp = EMAIL_USERNAME.rsplit("@", 1)
    username = temp[0].strip()
    domain = temp[1].strip()
    return f"{username}+{EMAIL_USERNAME_POSTFIX}{user_id}@{domain}".lower()


def launch_browser(pw: Playwright):
    """
    Launch the browser.
    """
    browser = pw.chromium.launch(
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
    context = browser.new_context()
    page = context.new_page()
    return browser, context, page


def login_user(page: Page, user_email: str):
    """
    Login to the Expensify app with OTP.
    """
    page.get_by_test_id("username").fill(user_email)
    page.get_by_role("button", name="Continue").click()
    page.get_by_role("textbox").fill('436232')

    # Wait for the main screen to appear
    page.get_by_test_id("BaseSidebarScreen").wait_for(state="visible", timeout=5000)


def test_removed_member_is_not_shown_in_a_group_chat_welcome_message():
    """
    Verify that the welcome message of a group chat does not include the removed member.
    """
    with sync_playwright() as pw:
        # Log in the admin user
        user_emails = [generate_recipient_email(user_id=str(i)) for i in range(1, 4)]
        admin_email = user_emails[0]
        first_name, last_name = "Fname", "Lname"

        browser, context, page = launch_browser(pw)
        # Open the Expensify app
        page.goto(EXPENSIFY_URL)
        login_user(page, admin_email)
        LOGGER.info("User logged in successfully")

        # Before executing the core test logic, make sure to leave the existing group chats to avoid reading stuff
        # from the wrong chat
        LOGGER.info("Leave the existing group chats")
        chat_names = (
            page.get_by_test_id("BaseSidebarScreen")
            .get_by_role("button", name="Navigates to a chat")
            .get_by_test_id("DisplayNamesWithTooltip")
            .all_inner_texts()
        )

        group_chat_locator = (
            page.get_by_test_id("BaseSidebarScreen")
            .get_by_role("button", name="Navigates to a chat")
            .get_by_text(f"{user_emails[1]},")
            .first
        )
        group_details_locator = page.locator(
            f'div[data-testid="DisplayNamesWithTooltip"]:has-text("{first_name}")'
        ).last

        for chat_name in chat_names:
            if f"{user_emails[1]}," in chat_name:
                # Open each group chat starting at the top of the list
                (group_chat_locator.click())
                # Open group details page
                group_details_locator.click()
                # Leave the group chat
                (
                    page.get_by_test_id("ReportDetailsPage")
                    .get_by_role("menuitem", name="Leave")
                    .click()
                )

        # Create a new group chat having all the users
        LOGGER.info("Create a group chat having all the users")
        page.get_by_label("Start chat (Floating action)").click()
        page.get_by_label("Start chat", exact=True).click()

        for user_email in user_emails[1:]:
            (
                page.get_by_test_id("NewChatPage")
                .get_by_test_id("selection-list-text-input")
                .fill(user_email)
            )
            (
                page.get_by_test_id("NewChatPage")
                .get_by_text(user_email)
                .first.wait_for(state="visible", timeout=2000)
            )
            (
                page.get_by_label(user_email)
                .get_by_role("button", name="Add to group")
                .click()
            )

        (page.get_by_test_id("NewChatPage").get_by_role("button", name="Next").click())
        (
            page.get_by_test_id("NewChatConfirmPage")
            .get_by_role("button", name="Start group")
            .click()
        )

        (group_chat_locator.click())
        welcome_message_locator = (
            page.get_by_test_id("report-actions-list")
            .locator('div:has-text("This chat is with")')
            .last
        )
        welcome_message_locator.wait_for(state="visible", timeout=5000)

        # Read the group welcome message
        LOGGER.info("Read the welcome message of the group chat")
        welcome_message = welcome_message_locator.inner_text()

        LOGGER.info("Welcome message: %s", welcome_message)

        # Remove a user from the group chat
        user_to_remove = user_emails[2]
        LOGGER.info("Remove %s from the group chat", user_to_remove)
        group_details_locator.click()
        (
            page.get_by_test_id("ReportDetailsPage")
            .get_by_role("menuitem", name="Members")
            .click()
        )
        (
            page.get_by_test_id("selection-list")
            .get_by_role("button", name=user_to_remove)
            .first.click()
        )
        (
            page.get_by_test_id("ReportParticipantDetails")
            .get_by_role("button", name="Remove from group")
            .click()
        )
        page.get_by_role("button", name="Remove", exact=True).click()
        (
            page.get_by_test_id("ReportParticipantsPage")
            .get_by_role("button", name="Back")
            .click()
        )
        (
            page.get_by_test_id("ReportDetailsPage")
            .get_by_role("button", name="Back")
            .click()
        )

        # Read the welcome message again
        welcome_message_locator.wait_for(state="visible", timeout=5000)

        expect(welcome_message_locator).not_to_contain_text(user_to_remove)

        # Cleanup
        context.close()
        browser.close()
