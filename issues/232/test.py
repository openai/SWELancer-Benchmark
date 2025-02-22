import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import re
import pytest
from playwright.sync_api import sync_playwright, expect, Page
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser

EMAIL = "Adebayovicktor0+test47282@gmail.com"
TWO_SECONDS = 2000
THREE_SECONDS = 3000
FIVE_SECONDS = 5000

def login_user(p: PlaywrightContextManager) -> tuple[Browser, Page, str]:
    user_email = EMAIL
    browser = p.chromium.launch(
        headless=True,
        proxy = {"server": "http://127.0.0.1:8080/"},
        args=[
        "--ignore-certificate-errors",
        "--disable-web-security", 
        "--disable-features=IsolateOrigins,site-per-process"
        ]
    )
    context = browser.new_context()
    page: Page = context.new_page()

    page.goto('https://dev.new.expensify.com:8082')
    phone_or_email_input = page.locator('input[type="email"]')
    expect(phone_or_email_input).to_be_visible()
    phone_or_email_input.fill(user_email)

    page.locator('button[tabindex="0"]').click()

    page.wait_for_timeout(1000)

    magic_code = '123456'
    page.wait_for_timeout(FIVE_SECONDS)
    validate_code_input = page.locator('input[name="validateCode"]').nth(0)
    expect(validate_code_input).to_be_visible()
    validate_code_input.fill(magic_code)
    page.wait_for_timeout(THREE_SECONDS)
    return browser, page, user_email

def check_members(page: Page, formatted_currency):
    page.get_by_label(f"Tracking {formatted_currency}", exact=False).first.click()
    page.wait_for_timeout(1000)
    members = page.locator("div").filter(has_text=re.compile(r"^Members$")).nth(3)
    assert not members.is_visible()


@pytest.mark.parametrize("first_name, last_name", [("Yagna", "Sai")])
def test_run(first_name: str, last_name: str) -> None:
    with sync_playwright() as playwright:
        amount = 9226
        formatted_amount = "{:,}".format(amount)
        browser, page, user_email = login_user(playwright)
        print(f"Logged in with email: {user_email}")
        page.wait_for_timeout(THREE_SECONDS)
        page.locator(
            'button[aria-label="Inbox"]').nth(-1).click()
        page.wait_for_timeout(TWO_SECONDS)
        page.locator('div[data-testid="DisplayNamesWithTooltip"]',
            has_text=f"{first_name} {last_name}").last.click()
        page.wait_for_timeout(TWO_SECONDS)
        page.get_by_label("Back").click()
        page.wait_for_timeout(TWO_SECONDS)
        page.locator(
            'button[aria-label="Create"]').last.click()
        page.wait_for_timeout(TWO_SECONDS)
        page.get_by_text("Track expense").click()
        page.get_by_text('Manual').last.click()
        page.get_by_placeholder("0").fill(str(amount))
        page.wait_for_timeout(TWO_SECONDS)
        page.get_by_role("button", name="Next").first.click()
        page.wait_for_timeout(TWO_SECONDS)
        currencies = page.get_by_test_id("IOURequestStepConfirmation").get_by_test_id(
            "selection-list"
        ).filter(has_text=formatted_amount).all_inner_texts()
        currencies = [item for item in currencies[0].split('\n') if formatted_amount in item]
        currency = currencies[0].split('\xa0')[0]
        page.get_by_role("button", name="Track expense").last.click()
        page.get_by_test_id("report-actions-list").get_by_text(f"{formatted_amount}.00").last.click()
        page.wait_for_timeout(TWO_SECONDS)
        check_members(page, currency)


        browser.close()

if __name__ == "__main__":
    pytest.main([__file__])
