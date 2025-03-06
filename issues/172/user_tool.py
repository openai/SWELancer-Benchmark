from typing import Any
from playwright._impl._page import Page
# from playwright._impl._locator import Locator
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from utils.trace_cleaner import trace_cleaner


EMAIL = "brighturing926+51316@gmail.com"
user_workspace_admin = "https://dev.new.expensify.com:8082/r/524783183199166"
invalid_member = "+1 631-791-8378"


def login_user(p: PlaywrightContextManager, user_email: str) -> Any:
    # Step 1: Open expensify url
    browser = p.chromium.launch(
        proxy={"server": "http://localhost:8080"}, 
        headless=False, 
        args=["--no-sandbox", "--disable-dev-shm-usage", "--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"], 
        slow_mo=500, 
        channel="chromium")
    context = browser.new_context()
    page = context.new_page()
    page.goto('https://dev.new.expensify.com:8082/')

    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()

    # Magic code entry
    my_otp_code = "123456"

    page.get_by_test_id("validateCode").fill(my_otp_code)

    # Click Optional sign in button
    try:
        page.get_by_role("button", name="Sign in").click()
    except Exception:
        pass

    return browser, page


def test_14513() -> Any:
    with sync_playwright() as p:
        browser, page = login_user(p, EMAIL)
        # Start tracing
        page.context.tracing.start(screenshots=True, snapshots=True, sources=True)
        try:
            # Step 1: Log in the user and begin test actions
            page.get_by_label("My settings").click()
            page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()
            page.get_by_label("New workspace").first.click()

            # page.pause()
            page.get_by_label("Members").click()
            page.get_by_role("button", name="Invite member").click()
            page.get_by_test_id("selection-list-text-input").fill(invalid_member)
            page.get_by_label(invalid_member).first.click()
            page.get_by_role("button", name="Next").click()
            page.get_by_test_id("WorkspaceInviteMessagePage").get_by_role("button", name="Invite").click()
            page.wait_for_timeout(3000)
            expect(page.get_by_test_id("WorkspaceInitialPage").get_by_text("Unable to add members to")).to_be_visible()
            page.get_by_label("Back").click()
            expect(page.get_by_text("Unable to add members to")).to_be_visible()

            page.wait_for_timeout(3000)
            page.get_by_label("Inbox").click()
            page.wait_for_timeout(3000)
            page.get_by_text(invalid_member).first.click()
            expect(page.get_by_text("Unexpected error creating")).to_be_visible()
        finally:
            trace_file = "/app/expensify/user_tool/output_browser1.zip"
            page.context.tracing.stop(path=trace_file)
            trace_cleaner(trace_file)
            browser.close()