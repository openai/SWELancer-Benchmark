import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import pytest
from utils.login import sign_up
from utils.browser import close_browser
from playwright.async_api import expect, async_playwright
from utils.trace_cleaner import trace_cleaner


@pytest.mark.asyncio
async def test_check_hover_style():
    derived_email = "testuserexpensify+7574132@gmail.com"
    trace_path = "/app/expensify/user_tool/output_browser1.zip"

    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(
        slow_mo=500,
        headless=True,
        proxy={
            'server': 'http://127.0.0.1:8080'
        },
        args=[
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process'
        ]
    )
    context = await browser.new_context(ignore_https_errors=True)

    # Start tracing
    await context.tracing.start(screenshots=True, snapshots=True, sources=True)

    page = await context.new_page()

    try:
        # Step 1: Login / Sign up
        await sign_up(page, derived_email)
        await expect(page.locator("text=What do you want to do today?")).to_be_visible()

        # Step 2: Select 'Track and budget expenses' and get styles before hover
        track_item = page.locator('div[aria-label="Track and budget expenses"]')
        await track_item.click()
        div_style_before_hover = await track_item.get_attribute("style")

        # Step 3: Hover over the div and get styles after
        box = await track_item.bounding_box()
        await page.mouse.move(box['x'], box['y'])
        div_style_after_hover = await track_item.evaluate("element => window.getComputedStyle(element).backgroundColor")

        # Step 4: Assert background after hover is in the div styles
        assert div_style_after_hover in div_style_before_hover, f"For the selected item, expected background after hover '{div_style_after_hover}' should be similar to before hover '{div_style_before_hover}'"

    finally:
        # Stop tracing and save the trace
        await context.tracing.stop(path=trace_path)
        # Call trace_cleaner
        trace_cleaner(trace_path)
        # Close browser
        await close_browser(context, page, playwright)
