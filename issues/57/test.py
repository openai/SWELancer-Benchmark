
"""
Verify that copying chat member's email to clipboard does not paste twice in private notes.

"""
import pytest
import os
from playwright.async_api import Page, expect, async_playwright
from utils.login import NEW_DOT_URL, sign_in
from utils.browser import close_browser, start_browser

STATIC_PREFIX = 53654
EXPENSIFY_USERNAME_FIRSTNAME = "osaidtest"
EXPENSIFY_USERNAME_LASTNAME = "testaccount"
EXPENSIFY_USERNAME = f"{EXPENSIFY_USERNAME_FIRSTNAME} {EXPENSIFY_USERNAME_LASTNAME}"
EXPENSIFY_EMAIL_USERNAME = "osaidtest5"
EXPENSIFY_EMAIL = f"osaidtest5+{STATIC_PREFIX}@gmail.com"
EXPENSIFY_PASSWORD = "ntvd acej mmaa qqmd"
DATA_DIR = "browser_context"
WORKSPACE_NAME = "workspace_1"
SLOW_MO = 1000
NORMAL_RUN = False
PROXY_SETTINGS = {"server": "http://localhost:8080"}
DM_LABEL='Concierge'
DM_EMAIL='concierge@expensify.com'


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
            proxy = {"server": "http://localhost:8080"}, headless = False, args = ["--no-sandbox", "--disable-dev-shm-usage", "--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"], slow_mo = slow_mo, channel = "chromium")
        context = await browser.new_context(
            ignore_https_errors=True, timezone_id="Asia/Karachi", permissions=["clipboard-read", "clipboard-write"], **device
        )
        page = await context.new_page()

    return context, page, playwright  # Return playwright to close later


@pytest.mark.asyncio(scope='session')
async def test_53654():
    try:
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

        # Step 1: Sign in
        if NORMAL_RUN:
            # Normal test run
            await sign_in(page, EXPENSIFY_EMAIL, password=EXPENSIFY_PASSWORD)
        else:
            # Recorded Test Run.
            await page.goto(NEW_DOT_URL)
            await sign_in_recorded(page=page, email=EXPENSIFY_EMAIL)
        
        
        await page.get_by_test_id('lhn-options-list').get_by_role('button', name='Navigates to a chat').filter(
            has=page.get_by_test_id('DisplayNamesWithTooltip').get_by_text(DM_LABEL)
        ).click()
        await page.get_by_label(DM_LABEL, exact=True).click()
        
        await page.get_by_label("Copy to clipboard").click()
        await page.get_by_label("Private notes").click()
        await page.get_by_role("textbox", name="Private notes").click()
        await page.keyboard.press("Control+V")
        await expect(page.get_by_test_id("PrivateNotesEditPage").get_by_text(DM_EMAIL, exact=True)).to_be_visible()
  

    finally:
        # Step 6: Close the browser.
        await close_browser(context, page, playwright)




