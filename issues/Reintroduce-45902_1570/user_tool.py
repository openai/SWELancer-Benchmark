import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import re
import pytest
from playwright.async_api import async_playwright, expect, Browser, BrowserContext, Page, TimeoutError
from playwright.async_api._context_manager import PlaywrightContextManager
from utils.trace_cleaner import trace_cleaner

EMAIL_ADMIN = "doorsqueaky+156289@gmail.com"
PASSWORD = "eabcahqraatorpvt"

WS_NAME = "Work_1754841161"

IMAP_SERVER = "imap.gmail.com"
EXPENSIFY = "https://dev.new.expensify.com:8082/"

MAX_TRIES = 5


def read_otp():
    """
        Returns a dummy otp
    """
    return "351846"


async def launch_browser(p: PlaywrightContextManager) -> tuple[Browser, BrowserContext, Page]:
    """
        Launches a new browser and opens a new page
    """
    browser = await p.chromium.launch(headless=True, slow_mo=600, args=["--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"])
    context = await browser.new_context()
    page = await context.new_page()

    return browser, context, page


async def login_newdot(page: Page, user_email: str):
    """
        Logs in a new user to expensify with a new team name
    """
    # step-1 Go to Expensify url
    await page.goto(EXPENSIFY)
    await page.wait_for_timeout(1000)

    # step-2 Fill in login details and login
    await page.locator('input[type="email"]').fill(user_email)
    await page.get_by_role('button', name="Continue").click()
    await page.wait_for_timeout(2000)

    try:
        # step-3 Enter OTP to login
        await page.wait_for_selector("text=Please enter the magic code sent to", timeout=5000)

        expensify_otp = read_otp()

        await page.locator('input[inputmode="numeric"]').fill(expensify_otp)
        await page.wait_for_selector('button[tabindex="0"]:has-text("Sign in")', timeout=3000)
    except TimeoutError:
        pass


async def navigate_to_expense_chat(page: Page, total_amount: int, ws_name: str):
    """
        Navigates to the expense chat
    """
    # step-1 Navigate to expense report. Requires tries to have both expenses appear
    await page.locator('button[aria-label="Navigates to a chat"]', 
                    has_text=re.compile(f".*{ws_name} owes .+{total_amount}.00")).click(timeout=30000)
    await page.wait_for_timeout(1000)
    
    # step-2 Check chat description
    chat_description = page.get_by_text(re.compile(f'Collaboration between Sharath Jadhav and {ws_name}.+')).last
    await expect(chat_description).to_be_visible(timeout=30000)
    await page.locator('button[aria-label="View details"]').last.click()
    await page.wait_for_timeout(1000)


async def check_expense_report(page: Page, amount: int, description: str):
    """
        Check expense report
    """
    # step-1 Check first expense button
    expense_locator = page.locator('div[aria-label="Cash"]')
    expense = expense_locator.get_by_text(re.compile(f'.+{amount}.00'))
    await expect(expense).to_be_visible(timeout=30000)

    await page.wait_for_timeout(1000)

    # step-2 Open first expense report, check header and navigate back
    await expense.click()
    header = page.get_by_role('button', name=re.compile(f'.+{amount}.00 for {description}')).first
    await expect(header).to_be_visible(timeout=30000)


async def check_expenses(page: Page, 
                         first_amount: int, first_desc: str,
                         second_amount: int, second_desc: str,
                         ws_name: str):
    """
        Holds the specified amount
    """
    total_amount = first_amount + second_amount

    # step-1 Check first expense
    await navigate_to_expense_chat(page, total_amount, ws_name)
    await check_expense_report(page, first_amount, first_desc)

    await page.wait_for_timeout(1000)

    # step-2 Check second expense
    await navigate_to_expense_chat(page, total_amount, ws_name)
    await check_expense_report(page, second_amount, second_desc)


async def force_offline(page: Page):
    """
        Forces offline under My settings
    """
    await page.locator('button[aria-label="My settings"]').click()
    await page.wait_for_timeout(1000)
    await page.locator('div[aria-label="Troubleshoot"]').click()
    await page.wait_for_timeout(1000)

    force_offline_toggle = page.locator('button[aria-label="Force offline"]')
    is_offline_toggled = (await force_offline_toggle.get_attribute('aria-checked')) == 'true'

    if not is_offline_toggled:
        await force_offline_toggle.click()
        await page.wait_for_timeout(1000)
    await page.locator('button[aria-label="Inbox"]').click()


async def approve_amount(page: Page, amount: int, ws_name: str):
    """
        Approves only the specified amount
   """
    # step-1 Navigate to expense report
    await page.locator('button[aria-label="Navigates to a chat"]', 
                       has_text=re.compile(f".*{ws_name} owes .+")).click()
    await page.wait_for_timeout(1000)
    await page.get_by_role('button', name="Approve").last.click()
    await page.wait_for_timeout(1000)

    # step-2 Approve only the amount specified
    await page.locator('button', has_text=re.compile(f"Approve only .+{amount}.00")).click()


async def approve_and_see(page: Page,  amount_to_approve: int, 
                          ws_name: str):
    """
        Holds one of the submitted expenses and approves another
    """
    # step-1 Force offline
    await force_offline(page)
    await page.wait_for_timeout(1000)

    # step-2 Approve amount
    await approve_amount(page, amount_to_approve, ws_name)

    # step-3 Navigate to chat and check svg
    ws_chat = page.locator('button[aria-label="Navigates to a chat"]', 
                           has_text=re.compile(f".*{ws_name} owes .+"))
    await expect(ws_chat).to_be_visible()
    await ws_chat.click()

    # step-4 Expect to be GBR'ed
    svg_element = ws_chat.locator('svg[fill="#03D47C"]')
    await expect(svg_element).not_to_be_visible()


async def navigate_hold_message(page: Page):
    """
        Navigates the hold message if present
    """
    try:
        await page.get_by_role('button', name="Got it").click()
    except TimeoutError:
        pass


async def cleanup(browser: Browser, page: Page):
    """
        Post test cleanup
    """
    await page.wait_for_timeout(1000)
    await browser.close()


@pytest.mark.asyncio
async def test_run():
    """
        Tests the GBR dot not to be visible on the workspace chat button
    """
    async with async_playwright() as pw:
        browser, context, page = await launch_browser(pw)
        output_trace_path = "/app/expensify/user_tool/output_browser1.zip"

        # Start tracing
        await context.tracing.start(screenshots=True, snapshots=True, title="test_run")

        try:
            # Login the admin account
            await login_newdot(page, EMAIL_ADMIN)

            # Navigate away from old chat message
            await navigate_hold_message(page)

            # Checks submitted expenses
            await check_expenses(page, 100, 'a', 200, 'yi', WS_NAME)

            # approve non-held amount and check GBR
            await approve_and_see(page, 100, WS_NAME)

            # Cleanup
            await cleanup(browser, page)
        except Exception as e:
            # Reraise after we ensure we stop tracing
            raise e
        finally:
            # Stop tracing and save
            await context.tracing.stop(path=output_trace_path)
            # Clean up the trace
            trace_cleaner(output_trace_path)
