import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page


def generate_random_email():
    return f"freelanceapptest+643895@gmail.com"



def login_user(page: Page, first_name="A", last_name="Khan") -> str:
    user_email = generate_random_email()


    page.goto('https://dev.new.expensify.com:8082/')


    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(1000)


    try:
        page.locator('button[tabindex="0"]').click()
        page.wait_for_timeout(1000)
    except Exception:
        pass


    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()
    page.wait_for_timeout(1000)


    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()
    page.wait_for_timeout(1000)

    return user_email




def set_default_currency(page: Page, search_text: str, currency: str) -> None:

    default_currency_button = page.locator('div[role="menuitem"]').get_by_text("Default currency")
    expect(default_currency_button).to_be_visible()
    default_currency_button.click()


    input_currency = page.locator('input[aria-label="Default currency"]')
    input_currency.fill(search_text)
    expect(page.get_by_test_id("WorkspaceProfileCurrencyPage")).to_contain_text(currency)




def check_currency_in_workspace_chat(page: Page) -> None:

    plus_icon = page.locator('button[aria-label="Start chat (Floating action)"]')
    expect(plus_icon).to_be_visible()
    plus_icon.click()


    new_workspace_button = page.locator('div[aria-label="New workspace"]')
    expect(new_workspace_button).to_be_visible()
    new_workspace_button.click()


    set_default_currency(page, 'rupee', "INR - ₹")


def test_currency_search():
    from utils.trace_cleaner import trace_cleaner
    trace_path = "/app/expensify/user_tool/output_browser1.zip"

    with sync_playwright() as p:
        browser = None
        context = None
        try:

            browser = p.chromium.launch(headless=True, args=[
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process"
            ])
            context = browser.new_context()
            context.tracing.start(screenshots=True, snapshots=True, sources=True)
            page = context.new_page()


            _ = login_user(page)


            check_currency_in_workspace_chat(page)

        except Exception as e:

            raise e
        finally:

            if context:
                context.tracing.stop(path=trace_path)
            trace_cleaner(trace_path)
            if browser:
                browser.close()
