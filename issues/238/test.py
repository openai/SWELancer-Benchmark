import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import pytest
from utils.login import sign_up, complete_onboarding
from utils.email_handler import get_unique_derived_email
from utils.browser import close_browser
from playwright.async_api import expect, async_playwright
from playwright._impl._browser import Browser
from playwright._impl._page import Page


async def start_browser(headless=True, mobile_device=None, launch_args=["--ignore-certificate-errors"]):

    playwright = await async_playwright().start()
    device_profile = playwright.devices[mobile_device] if mobile_device else {}
    browser = await playwright.chromium.launch(headless=headless, args=launch_args)
    context = await browser.new_context(ignore_https_errors=True, **device_profile)
    page = await context.new_page()
    return context, page, playwright


async def track_expense(page: Page):

    await page.locator('button[aria-label="Start chat (Floating action)"]').click()


    await page.locator('div[aria-label="Track expense"]').click()


    await page.locator('button:has-text("Got it")').click()


    await page.locator('button[aria-label="Manual"]').click()


    await page.locator('input[role="presentation"]').fill("50")


    await page.locator('button[data-listener="Enter"]', has_text="Next").first.click()


    await page.locator('button:has-text("Track expense")').click()



@pytest.mark.asyncio
async def test_issue_46374():
    """
    Sign up and check if Inbox is visible
    """


    original_email = "testuserexpensify@gmail.com"
    derived_email = "testuserexpensify+15114188@gmail.com"


    context, page, playwright = await start_browser(launch_args=[
        '--disable-web-security',
        '--disable-features=IsolateOrigins,site-per-process'
    ], mobile_device='iPhone 12 Pro')


    await sign_up(page, derived_email)


    try:
        await complete_onboarding(page)
    except Exception:
        pass


    await expect(page.get_by_label("Inbox")).to_be_visible()
    await page.mouse.click(0,0)


    await track_expense(page)
    await page.wait_for_timeout(1000)


    back_button = page.locator('button[aria-label="Back"]')
    await back_button.wait_for()
    await back_button.click()

    await page.wait_for_timeout(4000)
    await page.locator('button[aria-label="Search"]').click()
    button = page.get_by_test_id('selection-list').locator('button[tabindex="0"]')
    await button.wait_for()


    await button.hover()
    await page.mouse.down()
    await page.wait_for_timeout(1000)
    await page.mouse.up()


    await page.locator('div[aria-label="Select"]').click()


    await page.locator('button:has-text("1 selected")').click()


    await page.locator('div[aria-label="Delete"]').click()


    await page.locator('button:has-text("Delete")').click()

    await page.wait_for_timeout(1000)
    b_button = page.locator('button[aria-label="Back"]')
    assert await b_button.count() == 0, "Back button was not found, This is accepted."


    await close_browser(context, page, playwright)
