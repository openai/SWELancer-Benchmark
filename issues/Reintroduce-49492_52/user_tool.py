import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

"""
Verify whether we can delete a saved entry using the Enter Key.

"""
import os
import pytest
from playwright.async_api import Page, expect, async_playwright
from utils.login import NEW_DOT_URL, sign_in
from utils.browser import close_browser
from utils.trace_cleaner import trace_cleaner  # <-- Added import

master_email_address = "brighturing926+49492@gmail.com"
master_app_password = "sijknxflhloopmta"
NORMAL_RUN = False
DATA_DIR = "browser_context"
SLOW_MO = 1000

async def start_browser(
    headless=True,
    persistent=False,
    data_dir=None,
    slow_mo=500,
    launch_args=["--ignore-certificate-errors"],
):
    """
    Start a browser instance with the given parameters.

    :param headless: Boolean to specify if the browser should run in headless mode.
    :param persistent: Boolean to specify if the browser context should be persistent.
    :param data_dir: Directory to store browser data for persistent context.
    :return: A tuple of (context, page, playwright).
    """

    # Initialize Playwright
    playwright = await async_playwright().start()
    context, page = None, None
    if persistent:
        if data_dir is None:
            data_dir = "browser_context"
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

        context = await playwright.chromium.launch_persistent_context(
            data_dir,
            headless=headless,
            args=launch_args,
            slow_mo=slow_mo,
            timezone_id="Asia/Karachi",
        )
        page = context.pages[0]
    else:
        browser = await playwright.chromium.launch(
            headless=headless, args=launch_args, slow_mo=slow_mo
        )
        context = await browser.new_context(
            ignore_https_errors=True, timezone_id="Asia/Karachi"
        )
        page = await context.new_page()

    return context, page, playwright  # Return playwright to close later

async def sign_in_recorded(page: Page, email: str):
    await page.get_by_test_id("username").fill(email)
    await page.get_by_role("button", name="Continue").click()
    await page.get_by_test_id("validateCode").fill("123456")

@pytest.mark.asyncio
async def test_enter_key_to_delete() -> None:

    context, page, playwright = await start_browser(
        persistent=False,
        data_dir=DATA_DIR,
        headless=True,
        slow_mo=SLOW_MO,
        launch_args=[
            "--ignore-certificate-errors",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
        ],
    )

    # Start trace
    await context.tracing.start(screenshots=True, snapshots=True)

    try:
        # Step 1: Sign in
        if NORMAL_RUN:
            # Normal test run
            await sign_in(page, master_email_address, password=master_app_password)
        else:
            # Recorded Test Run.
            await page.goto(NEW_DOT_URL)
            await sign_in_recorded(page=page, email=master_email_address)

        await page.get_by_test_id("CustomBottomTabNavigator").get_by_label("Search").click()
        await page.get_by_role("button", name="Filters").click()
        await page.get_by_test_id("SearchAdvancedFiltersPage").get_by_role("menuitem", name="Category").click()
        await page.locator("#Equipment").click()
        await page.get_by_role("button", name="Save").click()
        await page.get_by_test_id("SearchAdvancedFiltersPage").get_by_role("menuitem", name="Currency").click()
        await page.get_by_test_id("selection-list-text-input").fill("usd")
        await page.locator("[id=\"USD\\ -\\ $\"]").click()
        await page.get_by_role("button", name="Save").click()
        await page.get_by_role("button", name="Save search").click()
        await page.get_by_label("More").click()
        await page.get_by_label("Delete").click()
        await page.locator("body").press("Enter")

        delete_model = page.get_by_role("button", name="Delete")
        await expect(delete_model).not_to_be_visible()
    except Exception as e:
        # Re-raise the exception so the test fails, but still proceed to finally.
        raise e
    finally:
        # Stop trace and save it
        await context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
        # Clean the trace
        trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
        # Close the browser.
        await close_browser(context, page, playwright)
