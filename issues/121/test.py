from typing import Any
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._page import Page


EMAIL = "brighturing926+52386@gmail.com"


def login_user(p: PlaywrightContextManager, email_address: str) -> Page:
    # Launch chromiun and open new page
    browser = p.chromium.launch(
        proxy = {"server": "http://localhost:8080"}, headless = False, args = ["--no-sandbox", "--disable-dev-shm-usage", "--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"], slow_mo = 200, channel = "chromium")
    page = browser.new_page()

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

    return page


def test_issue_52386() -> Any:
    with sync_playwright() as p:
        # Step 1: Log in the user and begin test actions
        page = login_user(p, EMAIL)
        page.wait_for_timeout(3000)

        page.get_by_label("Start chat (Floating action)").click()
        page.get_by_label("Split expense").click()
        page.get_by_label("Manual").click()
        page.get_by_label("Select a currency").click()
        page.get_by_test_id("selection-list-text-input").fill("usd")
        page.get_by_label("USD - $").click()
        page.get_by_placeholder("0").fill("2")
        page.wait_for_timeout(2000)

        # Click Next instead of Split expense
        expect(page.get_by_role("button", name="Split expense")).not_to_be_visible()
        page.get_by_role("button", name="Next").first.click()
        page.wait_for_timeout(2000)

        page.get_by_text("Amount").click()
        expect(page.get_by_role("button", name="Split expense")).not_to_be_visible()
        page.get_by_role("button", name="Save").click()
