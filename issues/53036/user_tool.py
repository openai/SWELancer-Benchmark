"
Verify that Save Search option is present on applying custom filters
""
import pytest
import os
from playwright.async_api import Page, expect, async_playwright
from utils.login import NEW_DOT_URL, sign_in
from utils.browser import close_browser, start_browser
from utils.trace_cleaner import trace_cleaner

STATIC_PREFIX = 53036
EXPENSIFY_USERNAME_FIRSTNAME = "osaidtest"
EXPENSIFY_USERNAME_LASTNAME = "testaccount"
EXPENSIFY_USERNAME = f"{EXPENSIFY_USERNAME_FIRSTNAME} {EXPENSIFY_USERNAME_LASTNAME}"
EXPENSIFY_EMAIL_USERNAME = "osaidtest5"
EXPENSIFY_EMAIL = f"osaidtest5+{STATIC_PREFIX}@gmail.com"
EXPENSIFY_PASSWORD = "ntvd acej mmaa qqmd"
DATA_DIR = "browser_context"
WORKSPACE_NAME = "workspace1"
SLOW_MO = 1000
NORMAL_RUN = False
PROXY_SETTINGS = {"server": "http://localhost:8080"}
SEARCH_QUERY = "type:expense status:all from:osaidtest5+530366@gmail.com to:osaidtest5+53036@gmail.com"
SECOND_USER_USERNAME = 'second usr'


async def sign_in_recorded(page: Page, email: str):
    await page.get_by_test_id("username").fill(email)
    await page.get_by_role("button", name="Continue").click()
    await page.get_by_test_id("validateCode").fill("123456")


async def start_browser(
    headless=False,
    persistent=False,
    data_dir=None,
    slow_mo=500,
    launch_args=["--ignore-certificate-errors"],
    proxy=None,
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
    device = playwright.devices["Desktop Safari"]
    context, page = None, None
    if persistent:
        if data_dir is None:
            data_dir = "browser_context"
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

        context = await playwright.chromium.launch_persistent_context(
            data_dir,
            proxy=proxy,
            headless=headless,
            args=launch_args,
            slow_mo=slow_mo,
            timezone_id="Asia/Karachi",
            **device
        )
        page = context.pages[0]
    else:
        browser = await playwright.chromium.launch(
            headless=headless, args=launch_args, slow_mo=slow_mo, proxy=proxy,
        )
        context = await browser.new_context(
            ignore_https_errors=True, timezone_id="Asia/Karachi", permissions=["clipboard-read", "clipboard-write"], **device
        )
        page = await context.new_page()

    return context, page, playwright  # Return playwright to close later


@pytest.mark.asyncio
async def test_53036():
    context, page, playwright = await start_browser(
        persistent=False,
        data_dir=DATA_DIR,
        headless=False,
        slow_mo=SLOW_MO,
        launch_args=[
            "--ignore-certificate-errors",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
        ],
        proxy=PROXY_SETTINGS
    )

    # Start tracing
    await context.tracing.start(screenshots=True, snapshots=True, sources=True)

    try:
        # Step 1: Sign in
        if NORMAL_RUN:
            # Normal test run
            await sign_in(page, EXPENSIFY_EMAIL, password=EXPENSIFY_PASSWORD)
        else:
            # Recorded Test Run.
            await page.goto(NEW_DOT_URL)
            await sign_in_recorded(page=page, email=EXPENSIFY_EMAIL)

        await page.get_by_test_id("CustomBottomTabNavigator").get_by_label("Search").click()

        # Cleanup (Reset Filters if present)
        await page.get_by_role("button", name="Filters").click()
        if await page.get_by_role("link", name="Reset filters").is_visible():
            await page.get_by_role("link", name="Reset filters").click()
        await page.get_by_label("Back").click()
        
        await page.get_by_test_id("Search").get_by_label("Search").click()
        await page.get_by_test_id("search-router-text-input").fill(SEARCH_QUERY)
        await page.get_by_test_id("search-router-text-input").press("Enter")

        await page.get_by_role("button", name="Filters").click()

        # Assert that the filters are correctly applied.
        await expect(page.get_by_test_id("SearchAdvancedFiltersPage").get_by_text(SECOND_USER_USERNAME)).to_be_visible()
        await expect(page.get_by_test_id("SearchAdvancedFiltersPage").get_by_text(EXPENSIFY_USERNAME)).to_be_visible()
        await expect(page.get_by_role("button", name="Save search")).to_be_visible()

    finally:
        trace_path = "/app/expensify/user_tool/output_browser1.zip"
        await context.tracing.stop(path=trace_path)
        trace_cleaner(trace_path)
        await close_browser(context, page, playwright)
