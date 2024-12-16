import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page


def get_user_email():
    return f"nitish.expensify+{64}@gmail.com"


def get_magic_code():
    return "123456"


def login_user(p: PlaywrightContextManager, first_name="Milan", last_name="T") -> tuple[Browser, Page, str]:
    browser = p.chromium.launch(headless=True, args=[
        "--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"],
        slow_mo=2000
    )

    page = browser.new_page()
    user_email = get_user_email()
    first_name = 'John'
    last_name = 'Doe'

    # Step 1: Open expensify url
    page.goto('https://dev.new.expensify.com:8082/')

    # Step 2: Enter email and click continue
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()

    try:
        expect(page.get_by_role("button", name="Sign in")).to_be_visible()
        page.get_by_test_id("validateCode").fill(get_magic_code())
    except Exception:
        page.get_by_role("button", name="Join").click()

    try:
        expect(page.locator('div[aria-label="Track and budget expenses"]').nth(0)).to_be_visible()

        # Step 4: Select 'Track and budget expenses' in onboarding page and click Continue
        page.locator('div[aria-label="Track and budget expenses"]').nth(0).click()

        # Step 5: Enter first name, last name and click continue
        page.locator('input[name="fname"]').nth(0).fill(first_name)
        page.locator('input[name="lname"]').nth(0).fill(last_name)
        page.get_by_role("button", name="Continue").nth(0).click()
    except Exception:
        pass

    try:
        get_started_here = page.locator('div', has_text="Get started here!").nth(-1)
        expect(get_started_here).to_be_visible()
        page.get_by_label("Close").nth(-1).click()
    except Exception:
        pass

    return browser, page


def test_check_background():
    with sync_playwright() as p:
        # Step 1: Login user
        browser, page = login_user(p)

        page.goto('https://dev.new.expensify.com:8082/settings/profile/status')

        # Step 2: Get the div element by its ID
        div_element = page.locator("#BaseOverlay")

        # Step 3: Check the style of the overlay
        tag_style = div_element.get_attribute("style")
        expected_tag_style = 'rgb(230, 225, 218)'
        assert expected_tag_style in tag_style, f"Expected overlay to have '{expected_tag_style}' background-color , but got '{tag_style}'"

        browser.close()
