import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page

from utils.trace_cleaner import trace_cleaner


def login_user(page: Page, first_name="Milan", last_name="T") -> None:
    user_email = "freelanceapptest+1733261135@gmail.com"

    # Step 1: Open expensify url
    page.goto('https://dev.new.expensify.com:8082/')

    # Step 2: Enter email and click continue
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(1000)

    # Step 3: Click join button (if present)
    try:
        page.locator('button[tabindex="0"]').click()
        page.wait_for_timeout(1000)
    except Exception:
        pass
    expect(page.locator("text=What do you want to do today?")).to_be_visible()

    # Step 4: Select 'Track and budget expenses' and click Continue
    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()
    page.wait_for_timeout(1000)

    # Step 5: Enter first/last names and click continue
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()
    page.wait_for_timeout(1000)


def open_submit_expense_and_click_on_next_button(page: Page) -> None:
    plus_icon = page.locator('button[aria-label="Start chat (Floating action)"]')
    expect(plus_icon).to_be_visible()
    plus_icon.click()
    page.wait_for_timeout(1000)

    new_workspace_button = page.locator('div[aria-label="Submit expense"]')
    expect(new_workspace_button).to_be_visible()
    new_workspace_button.click()
    page.wait_for_timeout(1000)

    manual_button = page.locator('button[aria-label="Manual"]')
    expect(manual_button).to_be_visible()
    manual_button.click()
    page.wait_for_timeout(1000)

    next_button = page.locator('button[data-tag="pressable"]', has_text='Next').last
    expect(next_button).to_be_visible()
    next_button.click()
    page.wait_for_timeout(2000)


def test_error_message_top_margin():
    with sync_playwright() as p:
        trace_path = "/app/expensify/user_tool/output_browser1.zip"
        browser = None
        context = None
        try:
            # Launch the browser, create a context, and start tracing
            browser = p.chromium.launch(headless=True, args=[
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process"
            ])
            context = browser.new_context()
            context.tracing.start(screenshots=True, snapshots=True, sources=True)

            page = context.new_page()

            # Step 1: Login user and open submit expense RHN
            login_user(page)
            open_submit_expense_and_click_on_next_button(page)

            # Step 2: A next button with 12px top margin should be visible below the error message
            #          and not 20px top margin
            next_button_20px = page.locator(
                'div[style="opacity: 1; border-radius: 100px; width: 100%; margin-top: 20px;"]', has_text='Next'
            ).last
            expect(next_button_20px).not_to_be_visible()
            page.wait_for_timeout(1000)

            next_button_12px = page.locator(
                'div[style="opacity: 1; border-radius: 100px; width: 100%; margin-top: 12px;"]', has_text='Next'
            ).last
            expect(next_button_12px).to_be_visible()
            page.wait_for_timeout(1000)

        except Exception as e:
            # Reraise or log if desired, but ensure we at least end up in 'finally'
            raise e
        finally:
            # Stop tracing, clean trace, close browser
            if context:
                context.tracing.stop(path=trace_path)
                trace_cleaner(trace_path)
            if browser:
                browser.close()
