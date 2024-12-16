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
from utils.trace_cleaner import trace_cleaner


async def start_browser(headless=True, mobile_device=None, launch_args=["--ignore-certificate-errors"]):
    # Initialize Playwright
    playwright = await async_playwright().start()
    device_profile = playwright.devices[mobile_device] if mobile_device else {}
    browser = await playwright.chromium.launch(headless=headless, args=launch_args)
    context = await browser.new_context(ignore_https_errors=True, **device_profile)
    page = await context.new_page()
    return context, page, playwright


async def track_expense(page: Page):
    # Click on the green plus button
    await page.locator('button[aria-label="Start chat (Floating action)"]').click()

    # Click on Track Expense
    await page.locator('div[aria-label="Track expense"]').click()

    # click on got it message
    await page.locator('button:has-text("Got it")').click()

    # click on Manual
    await page.locator('button[aria-label="Manual"]').click()

    # Enter the amount
    await page.locator('input[role="presentation"]').fill("50")

    # Click on Next button
    await page.locator('button[data-listener="Enter"]', has_text="Next").first.click()

    # click on tack expense
    await page.locator('button:has-text("Track expense")').click()


# Test function
@pytest.mark.asyncio
async def test_issue_46374():
    """
    Sign up and check if Inbox is visible
    """

    # Set up the email to use for the test
    original_email = "testuserexpensify@gmail.com"
    derived_email = "testuserexpensify+15114188@gmail.com"

    # Create trace path
    trace_path = "/app/expensify/user_tool/output_browser1.zip"

    # Start browser
    context, page, playwright = await start_browser(launch_args=[
        '--disable-web-security',
        '--disable-features=IsolateOrigins,site-per-process'
    ], mobile_device='iPhone 12 Pro')

    # Start tracing
    await context.tracing.start(title="test_issue_46374", screenshots=True, snapshots=True, sources=True)

    try:
        # Step 1: Login / Sign up
        await sign_up(page, derived_email)

        # Complete onboarding
        try:
            await complete_onboarding(page)
        except Exception:
            pass

        # Check if the Inbox is visible
        await expect(page.get_by_label("Inbox")).to_be_visible()
        await page.mouse.click(0,0)

        # Step 2: Track expense
        await track_expense(page)
        await page.wait_for_timeout(1000)

        # Step 3: Go back and Click on search
        back_button = page.locator('button[aria-label="Back"]')
        await back_button.wait_for()
        await back_button.click()

        await page.wait_for_timeout(4000)
        await page.locator('button[aria-label="Search"]').click()
        button = page.get_by_test_id('selection-list').locator('button[tabindex="0"]')
        await button.wait_for()

        # Long press on the expense.
        await button.hover()
        await page.mouse.down()
        await page.wait_for_timeout(1000)
        await page.mouse.up()

        # click on select button
        await page.locator('div[aria-label="Select"]').click()

        # click on 1 selected
        await page.locator('button:has-text("1 selected")').click()

        # Click on delete
        await page.locator('div[aria-label="Delete"]').click()

        # Confirm delete
        await page.locator('button:has-text("Delete")').click()

        await page.wait_for_timeout(1000)
        b_button = page.locator('button[aria-label="Back"]')
        assert await b_button.count() == 0, "Back button was not found, This is accepted."
    except Exception as e:
        # We raise the exception so the test result is reported correctly.
        raise e
    finally:
        # Stop tracing and save
        await context.tracing.stop(path=trace_path)
        # Clean trace
        trace_cleaner(trace_path)
        # Close browser
        await close_browser(context, page, playwright)
