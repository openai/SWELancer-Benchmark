import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page
import re
from playwright.sync_api import sync_playwright

# Constants for URLs and credentials
NEWDOT_URL = "https://dev.new.expensify.com:8082/"
OLDDOT_URL = "http://localhost:9000/"
EMAIL = "ikhanle001+100@gmail.com"
PASSWORD = "dzcr knad otxp bsuz"


def login_user(p: PlaywrightContextManager) -> tuple[Browser, Page, str]:
    browser = p.chromium.launch(
        headless=True,
        slow_mo=1000,
        args=["--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"],
        proxy={"server": "http://localhost:8080"}
    )
    page = browser.new_page()
    user_email = EMAIL
    page.goto('https://dev.new.expensify.com:8082/')
    page.locator('input[type="email"]').fill(user_email)
    page.get_by_role("button", name="Continue").nth(0).click()
    otp = "123456"
    page.locator('input[data-testid="validateCode"]').fill(otp)
    return browser, page, user_email


def submit_expense_in_workspace_chat(
        browser: Browser,
        page: Page,
        user_email: str,
        workspace_name,
        amount: str = "1000"
) -> tuple[Browser, Page, str]:
    # Step 1: Click on workspace chat
    workspace_chat = page.locator('button[aria-label="Navigates to a chat"]', has_text=workspace_name).first
    workspace_chat.click()

    # Step 2: Click on "+" icon and click submit expense
    plus_create_icon = page.locator('button[aria-label="Create"]').last
    plus_create_icon.click()

    submit_expense_button = page.locator('div[aria-label="Submit expense"]')
    submit_expense_button.click()

    # Step 3: Click on "Manual" button and enter amount
    manual_button = page.locator('button[aria-label="Manual"]')
    manual_button.click()

    page.locator('input[role="presentation"]').fill(amount)

    # Step 4: Click on Next button
    next_button = page.locator('button[data-listener="Enter"]', has_text="Next").first
    next_button.click()

    # Step 5: Add merchant details
    merchant_field = page.locator('div[role="menuitem"]', has_text="Merchant").last
    merchant_field.click()

    page.locator('input[aria-label="Merchant"]').fill("https://staging.new.expensify.com/r/575354256634947/165034783536884819")

    save_button = page.locator('button', has_text="Save")
    save_button.click()

    # Step 6: Submit the expense
    save_button = page.locator('button[data-listener="Enter"]', has_text="Submit")
    save_button.click()

    return browser, page, user_email


def test_save_description_in_submitted_expense():
    from utils.trace_cleaner import trace_cleaner
    with sync_playwright() as p:
        trace_path = "/app/expensify/user_tool/output_browser1.zip"
        browser, page, user_email = login_user(p)
        context = page.context

        # Start playwright tracing
        context.tracing.start(screenshots=True, snapshots=True, sources=True)

        try:
            # Step 2: Click on + icon and click on "New workspace"
            page.click('//button[@aria-label="My settings"]')
            page.click('//div[@aria-label="Workspaces"]')

            page.click('//button[@aria-label="New workspace"]')
            workspace_name_div = page.locator('//div[contains(text(), "Name")]/following-sibling::div[1]/div')
            workspace_name = workspace_name_div.text_content(timeout=15000)

            # Step 3: Click on Back arrow to go back and navigate to inbox screen
            back_arrow_button = page.locator('button[aria-label="Back"]')
            back_arrow_button.click()

            inbox_menu = page.locator('button[aria-label="Inbox"]')
            inbox_menu.click()

            # Step 4: Submit an expense
            browser, page, user_email = submit_expense_in_workspace_chat(browser, page, user_email, workspace_name)

            page.get_by_role("button", name=re.compile(r'Pay .+ elsewhere')).click()
            page.get_by_label("View details").click()

            page.set_viewport_size({'width': 375, 'height': 812})

            container = page.locator('div[aria-label="https://staging.new.expensify.com/r/575354256634947/165034783536884819"]')
            text_div = container.locator('div:text("https://staging.new.expensify.com/r/575354256634947/165034783536884819")')

            client_width = text_div.evaluate("el => el.clientWidth")
            scroll_width = text_div.evaluate("el => el.scrollWidth")

            assert client_width == scroll_width
        except Exception:
            # We re-raise after the finally block so test frameworks see the failure
            raise
        finally:
            # Stop tracing and clean
            context.tracing.stop(path=trace_path)
            trace_cleaner(trace_path)
            browser.close()
