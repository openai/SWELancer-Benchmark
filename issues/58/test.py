import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page

TEST_URL = "https://dev.new.expensify.com:8082/"
USER_EMAIL = "xecuycismfsga+k1nrfwcn@gmail.com"


def wait(page, for_seconds=1):
    page.wait_for_timeout(for_seconds * 1000)


def login(p: PlaywrightContextManager, if_phone=False) -> tuple[Browser, Page, str]:

    browser = p.chromium.launch(
        headless=True,
        args=[
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
        ],
    )

    if if_phone:
        phone = p.devices['iPhone 12 Pro']
        context = browser.new_context(
            **phone,
            permissions=['clipboard-read', 'clipboard-write'],
            reduced_motion='no-preference',
        )
    else:
        context = browser.new_context()

    page = context.new_page()

    page.goto(TEST_URL, timeout=120000)

    phone_or_email_input = page.locator('input[type="email"]')
    expect(phone_or_email_input).to_be_visible()
    phone_or_email_input.fill(USER_EMAIL)

    continue_button = page.locator('button[tabindex="0"]')
    expect(continue_button).to_be_visible()
    continue_button.click()


    wait(page)

    join_button = page.locator('button:has-text("Join")')
    if join_button.count() > 0:
        print("Join button found. This is a new user.")
        join_button.click()
    else:
        print("Join button not found. This is an existing user. Use Magic Code to sign in.")
        magic_code = "123456"
        print(f"Magic code: {magic_code}")

        validate_code_input = page.locator('input[data-testid="validateCode"]')
        expect(validate_code_input).to_be_visible()
        validate_code_input.fill(magic_code)

    return browser, page


def test_submit_expense_domain_recipient():
    with sync_playwright() as p:

        browser, page = login(p)


        plus_icon = page.locator('button[aria-label="Start chat (Floating action)"]')
        expect(plus_icon).to_be_visible()
        plus_icon.click()


        submit_expense_button = page.locator('div[aria-label="Submit expense"]')
        expect(submit_expense_button).to_be_visible()
        submit_expense_button.click()


        manual_button = page.locator('button[aria-label="Manual"]')
        expect(manual_button).to_be_visible()
        manual_button.click()


        page.locator('input[role="presentation"]').fill("20")


        next_button = page.locator("#numPadContainerView").get_by_role("button", name="Next")
        expect(next_button).to_be_visible()
        next_button.click()


        input_recipient = page.get_by_test_id("selection-list-text-input")
        expect(input_recipient).to_be_visible()
        input_recipient.fill("+@applause.expensifail.com")


        wait(page, 3)


        expect(page.get_by_text("No results found")).to_be_visible()

        browser.close()
