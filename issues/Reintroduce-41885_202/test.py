import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

"""
Verify whether the self-dm page content has bold style.

"""

import os
import pytest
from playwright.async_api import Page, expect, async_playwright
from utils.login import NEW_DOT_URL, sign_in
from utils.browser import close_browser

STATIC_PREFIX = "41185_2p1"
EXPENSIFY_USERNAME_FIRSTNAME = "osaidtest"
EXPENSIFY_USERNAME_LASTNAME = "testaccount"
EXPENSIFY_USERNAME = f"{EXPENSIFY_USERNAME_FIRSTNAME} {EXPENSIFY_USERNAME_LASTNAME}"
EXPENSIFY_EMAIL_USERNAME = "osaidtest5"
EXPENSIFY_EMAIL = f"osaidtest5+{STATIC_PREFIX}@gmail.com"
EXPENSIFY_PASSWORD = "ntvd acej mmaa qqmd"
DATA_DIR = "browser_context"
SLOW_MO = 1000
NORMAL_RUN = False 

# email: osaidtest5+41185_2p1@gmail.com

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
async def test_check_selfdm_isbold():
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

    # Step 1: Sign in
    if NORMAL_RUN:
        # Normal test run
        await sign_in(page, EXPENSIFY_EMAIL, password=EXPENSIFY_PASSWORD)
    else:
        # Recorded Test Run.
        await page.goto(NEW_DOT_URL)
        await sign_in_recorded(page=page, email=EXPENSIFY_EMAIL)


    # Step 2: Check if the self DM exists
    selfdm_span = page.locator('span', has_text=f"{EXPENSIFY_USERNAME} (you)")
    await selfdm_span.wait_for()

    # Step 3: Check the style of the selfdm name
    tag_style = await selfdm_span.get_attribute("style")
    expected_tag_style = 'font-weight: 700;'
    assert  expected_tag_style in tag_style, f"Expected self DM name to have '{expected_tag_style}', but got '{tag_style}'"

    # Close the browser.
    await close_browser(context, page, playwright)