import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page
from utils.email_handler import get_unique_derived_email
from utils.trace_cleaner import trace_cleaner

EMAIL = "testotpverif@gmail.com"
TIMEOUT = 200000
URL = 'https://dev.new.expensify.com:8082/'


def initialize_page_context(p: PlaywrightContextManager) -> tuple[Browser, Page]:
    # Launch chromium and open a new page
    browser = p.chromium.launch(headless=True, args=[
        "--ignore-certificate-errors",
        "--disable-web-security",
        "--disable-features=IsolateOrigins,site-per-process"
    ], proxy={"server": "http://localhost:8080"}, slow_mo=500)
    context = browser.new_context()
    page = context.new_page()
    page.set_default_navigation_timeout(TIMEOUT)
    page.set_default_timeout(TIMEOUT)
    page.goto(URL)
    return browser, page


def login_user(page: Page, email: str, first_name="Milan", last_name="T") -> str:
    # Step 1: Enter email and click continue
    page.locator('input[type="email"]').fill(email)
    page.locator('button[tabindex="0"]').click()

    # Step 2: Click join button
    try:
        page.locator('button[tabindex="0"]').click()
    except Exception:
        pass

    onboarding_screen = page.locator("text=What do you want to do today?")
    expect(onboarding_screen).to_be_visible()

    # Step 3: Select 'Something else' in onboarding page and click Continue
    something_else_button = page.locator('div[aria-label="Something else"]')
    expect(something_else_button).to_be_visible()
    something_else_button.click()

    # Step 5: Enter first name, last name and click continue
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()


def logout_user(page: Page) -> str:
    account_settings_button  = page.get_by_role('button', name='My Settings')
    account_settings_button.click()
    signout_button  = page.get_by_role('menuitem', name='Sign out')
    signout_button.click()


def test_manual_expense_description_cursor_should_not_overlap_with_text_content():
    with sync_playwright() as p:
        browser, page = initialize_page_context(p)
        context = page.context
        # Start trace recording
        context.tracing.start(
            title="Test Trace",
            screenshots=True,
            snapshots=True
        )
        try:
            # Email of the first logged in user.
            derived_email_1 = get_unique_derived_email(EMAIL)
            derived_email_1 = 'testotpverif+1734348660@gmail.com'
            login_user(page, derived_email_1, 'User', 'One')
            logout_user(page)

            # Login second user.
            derived_email_2 = get_unique_derived_email(EMAIL)
            derived_email_2 = 'testotpverif+1734348670@gmail.com'
            login_user(page, derived_email_2, 'User', 'Two')

            # Submit a new expense
            create_button = page.locator('button[aria-label="Start chat (Floating action)"]')
            create_button.click(timeout=TIMEOUT)

            submit_expense_button = page.get_by_role('menuitem', name='Submit expense')
            submit_expense_button.click()

            # click Manual expense option
            manual_expense_button = page.get_by_role('button', name='Manual')
            manual_expense_button.click()

            # Enter expense amount
            page.get_by_placeholder('0').fill('100')
            page.locator('#numPadContainerView').get_by_role('button', name= 'Next' ).click()

            # Search user 1 to submit expense to.
            page.get_by_test_id('selection-list-text-input').click()
            page.get_by_test_id('selection-list-text-input').fill(derived_email_1)
            page.get_by_label(derived_email_1).click()

            # Enter description.
            page.get_by_role('menuitem',name= 'Description' ).get_by_role('img').click()
            page.get_by_role('textbox',name= "What's it for?").fill('> hey')

            # Verification step: Check to see if padding right is any non-zero value.
            blockquote_element = page.locator('span[data-type="blockquote"]')
            expect(blockquote_element).to_have_css('padding-right', '1px')
        except Exception as e:
            raise e
        finally:
            # Stop and save trace
            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            # Clean the trace
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            browser.close()
