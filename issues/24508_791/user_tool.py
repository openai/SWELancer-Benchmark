import sys, os
from utils.trace_cleaner import trace_cleaner

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._page import Page

FIRST_NAME = "Milan"
LAST_NAME = "T"


def get_user_email():
    return f"nitish.expensify+{92}@gmail.com"


def login_user(p: PlaywrightContextManager):
    browser = p.chromium.launch(
        headless=True,
        args=["--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"],
        slow_mo=2000
    )
    context = browser.new_context()
    page = context.new_page()
    user_email = get_user_email()

    page.goto('https://dev.new.expensify.com:8082/')

    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()

    try:
        expect(page.get_by_role("button", name="Sign in")).to_be_visible()
        page.get_by_test_id("validateCode").fill("123456")
    except Exception:
        page.get_by_role("button", name="Join").click()

    return browser, context, page


def navigate_to_profile(page: Page):
    page.locator('button[aria-label="My settings"]').click()
    page.locator('div[aria-label="Profile"]').first.click()


def edit_legal_name(page: Page):
    page.locator('div[role="menuitem"]', has_text="Legal name").click()

    fname_input_field = page.locator('div[aria-label="Legal first name"] input')
    lname_input_field = page.locator('div[aria-label="Legal last name"] input')
    save_button = page.get_by_role('button', name="Save")

    fname_input_field.fill(FIRST_NAME + '÷×')
    lname_input_field.fill(LAST_NAME + '÷×')
    save_button.click()
    error_msg = page.get_by_text("Name can only include Latin characters.").all()
    assert len(error_msg) == 2


def test_fake_assignee_name_removed():
    with sync_playwright() as p:
        browser, context, page = login_user(p)
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        try:
            navigate_to_profile(page)
            edit_legal_name(page)
        except Exception as e:
            raise e
        finally:
            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            browser.close()