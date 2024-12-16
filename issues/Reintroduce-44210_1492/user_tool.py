import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import pytest
from utils.login import sign_up, complete_onboarding
from utils.browser import close_browser
from utils.trace_cleaner import trace_cleaner
from playwright.async_api import expect, async_playwright
from playwright._impl._page import Page


async def check_if_wrapped(element):
    is_wrapped = await element.evaluate(
        """(element) => {
            const lineHeight = parseFloat(getComputedStyle(element).lineHeight);
            const lines = element.clientHeight / lineHeight;
            return lines > 1;
        }"""
    )

    return is_wrapped


# Test function
@pytest.mark.asyncio
async def test_workspace_header():
    derived_email = "testuserexpensify+25215188@gmail.com"

    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(
        headless=True,
        proxy={
            'server': 'http://127.0.0.1:8080'
        },
        args=[
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process'
        ]
    )
    context = await browser.new_context(
        ignore_https_errors=True,
        viewport={
            "width": 375,
            "height": 812
        }
    )

    # Start tracing
    await context.tracing.start(
        title="test trace",
        screenshots=True,
        snapshots=True,
        sources=True
    )

    page = await context.new_page()

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
        await page.locator('button[aria-label="My settings"]').click()
        await page.locator('div[aria-label="Workspaces"]').click()

        back_button_parent = page.locator("#backButton").locator("..")
        workspaces_div = back_button_parent.locator("div", has_text="Workspaces").last

        if await workspaces_div.count() == 0:
            print("No 'Workspaces' div found.")
            return None

        is_wrapped = await check_if_wrapped(workspaces_div)
        assert not is_wrapped, "Workspaces header is wrapped into multiple lines!"

    finally:
        # Stop tracing, export, and clean up the trace
        await context.tracing.stop()
        trace_path = "/app/expensify/user_tool/output_browser1.zip"
        await context.tracing.export(path=trace_path)
        trace_cleaner(trace_path)

        # Close browser
        await close_browser(context, page, playwright)
