import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page
import time

from utils.trace_cleaner import trace_cleaner

#### CONFIG

TEST_URL = "https://dev.new.expensify.com:8082/"
USER_NAME = "expensify31"
USER_PASSWORD = "Pass@123456"


#### UTILS

def get_test_user_info(seed = None):
    if seed is None:
        return {"email": f"{USER_NAME}@gmail.com", "password": USER_PASSWORD, "first_name": f"{USER_NAME}", "last_name": "Test"}
    if type(seed) == type(True):
        seed = int(time.time())

    return {"email": f"{USER_NAME}+{seed}@gmail.com", "password": USER_PASSWORD, "first_name": f"Test", "last_name": "User"}

def wait(page, for_seconds=1):
    page.wait_for_timeout(for_seconds * 1000)



def login(p: PlaywrightContextManager, user_info, if_phone=False) -> tuple[Browser, Page, str]:
    permissions = ['clipboard-read', 'clipboard-write']
    browser = p.chromium.launch(headless=True,
                                args =[
            '--ignore-certificate-errors',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
        ])

    if if_phone:
        phone = p.devices['iPhone 12 Pro']
        context = browser.new_context(**phone, permissions=permissions, reduced_motion='no-preference')
    else:
        context = browser.new_context()

    page = context.new_page()

    page.goto(TEST_URL, timeout=120000)

    phone_or_email_input = page.locator('input[type="email"]')
    expect(phone_or_email_input).to_be_visible()
    phone_or_email_input.fill(user_info["email"])

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


def test_manual_expense_description_cursor_should_not_overlap_with_text_content():
    with sync_playwright() as p:
        # Login user
        user_info = get_test_user_info(seed=None)
        browser, page = login(p, user_info, False)
        context = page.context
        # Start tracing
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        try:
            page.wait_for_timeout(2000)
            email1= "random212@gmail.com"
            # Submit a new expense
            create_button = page.locator('button[aria-label="Start chat (Floating action)"]')
            create_button.click(timeout=2000)

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
            page.get_by_test_id('selection-list-text-input').fill(email1)
            page.get_by_label(email1).click()

            # Enter description.
            page.get_by_role('menuitem',name= 'Description' ).get_by_role('img').click()
            page.get_by_role('textbox',name= "What's it for?").fill('> hey')

            # Verification step: Check to see if padding right is any non-zero value.
            blockquote_element = page.locator('span[data-type="blockquote"]')
            expect(blockquote_element).to_have_css('padding-right', '1px')
        except Exception as e:
            # Re-raise the exception so the test fails
            raise e
        finally:
            # Stop tracing and clean the trace, ensuring it happens even if the test fails
            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")

        browser.close()
