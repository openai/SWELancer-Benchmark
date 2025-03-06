import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager


def get_user_email():
    return f"nitish.expensify+{9}@gmail.com"


def get_magic_code():
    return "123456"


def login_user(p: PlaywrightContextManager):
    browser = p.chromium.launch(headless=True, args=[
        "--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"],
        slow_mo=1000)

    page = browser.new_page()
    user_email = get_user_email()
    first_name = 'John'
    last_name = 'Doe'


    page.goto('https://dev.new.expensify.com:8082/')


    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()

    try:
        expect(page.get_by_role("button", name="Sign in")).to_be_visible()
        page.get_by_test_id("validateCode").fill(get_magic_code())
    except Exception:
        page.get_by_role("button", name="Join").click()

    try:
        expect(page.locator('div[aria-label="Track and budget expenses"]').nth(
            0)).to_be_visible()


        page.locator(
            'div[aria-label="Track and budget expenses"]').nth(0).click()


        page.locator('input[name="fname"]').nth(0).fill(first_name)
        page.locator('input[name="lname"]').nth(0).fill(last_name)
        page.get_by_role("button", name="Continue").nth(0).click()
    except Exception:
        pass

    try:
        get_started_here = page.locator(
            'div', has_text="Get started here!").nth(-1)
        expect(get_started_here).to_be_visible()
        page.get_by_label("Close").nth(-1).click()
    except Exception:
        pass

    return browser, page


def test_26228():
    with sync_playwright() as p:
        browser, page = login_user(p)

        plus_icon = page.locator(
            'button[aria-label="Start chat (Floating action)"]')
        expect(plus_icon).to_be_visible()
        plus_icon.click()

        start_chat_button = page.locator('div[aria-label="Start chat"]')
        expect(start_chat_button).to_be_visible()
        start_chat_button.press("Enter")

        inputBox = page.get_by_test_id("selection-list-text-input")
        expect(inputBox).to_be_visible()

        browser.close()
