from typing import Any
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._page import Page
from utils.trace_cleaner import trace_cleaner

EMAIL = "brighturing926+52639@gmail.com"
members = (
    "brighturing926+526391@gmail.com",
    "brighturing926+526392@gmail.com",
    "brighturing926+526393@gmail.com"
)
new_member = "brighturing926+526395@gmail.com"


def login_user(p: PlaywrightContextManager, email_address: str) -> (Any, Any, Page):
    # Launch chromium and open new page
    browser = p.chromium.launch(
        proxy={"server": "http://localhost:8080"},
        headless=False,
        args=["--no-sandbox", "--disable-dev-shm-usage", "--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"],
        slow_mo=500,
        channel="chromium"
    )
    # Create a new context and start tracing
    context = browser.new_context()
    context.tracing.start(screenshots=True, snapshots=True, sources=True)
    page = context.new_page()

    # Step 1: Open expensify url
    page.goto("https://dev.new.expensify.com:8082/")

    page.locator('input[type="email"]').fill(email_address)
    page.locator('button[tabindex="0"]').click()

    # Magic code entry
    my_otp_code = "123456"
    print(my_otp_code)

    page.get_by_test_id("validateCode").fill(my_otp_code)

    # Step 3: Click join button
    try:
        page.get_by_role("button", name="Sign in").click()
    except Exception:
        pass

    return browser, context, page


def test_issue_52639() -> Any:
    with sync_playwright() as p:
        browser, context, page = login_user(p, EMAIL)
        try:
            page.get_by_label("Start chat (Floating action)").click()
            page.get_by_label("Start chat", exact=True).click()
            for user in members:
                page.get_by_test_id("selection-list-text-input").click()
                page.get_by_test_id("selection-list-text-input").fill(user)
                page.wait_for_timeout(2000)
                page.get_by_role("button", name="Add to group").first.click()

            page.get_by_role("button", name="Next").click()
            page.get_by_role("button", name="Start group").click()
            page.get_by_label("Abi, Alice, Niki, Suzy").click()
            page.get_by_label("Members").click()
            page.get_by_role("button", name="Invite member").click()
            page.get_by_test_id("selection-list-text-input").click()
            page.get_by_test_id("selection-list-text-input").fill(new_member)

            page.wait_for_timeout(3000)
            expect(page.get_by_label("Aggrey Fish").or_(page.get_by_label(new_member)).locator("svg[id^='default-avatar']")).to_be_visible()
        finally:
            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            context.tracing.stop(path=trace_path)
            trace_cleaner(trace_path)
            browser.close()