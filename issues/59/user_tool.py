import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import re
import pytest
from utils.login import sign_up, complete_onboarding
from utils.browser import close_browser
from playwright.async_api import expect, async_playwright
from playwright._impl._page import Page
from utils.trace_cleaner import trace_cleaner


async def start_browser_with_proxy():
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
    page = await context.new_page()
    return context, page, playwright



@pytest.mark.asyncio
async def test_delete_expense_with_comments():
    trace_path = "/app/expensify/user_tool/output_browser1.zip"
    

    context, page, playwright = await start_browser_with_proxy()

    await context.tracing.start(screenshots=True, snapshots=True, sources=True)

    try:

        derived_email = "testuserexpensify+26443232@gmail.com"


        await sign_up(page, derived_email)


        try:
            await complete_onboarding(page)
        except Exception:
            pass


        await expect(page.get_by_label("Inbox")).to_be_visible()
        await page.get_by_label("Start chat (Floating action)").click()
        await page.get_by_text("Submit expense").first.click()


        await page.get_by_label("Manual").click()
        await page.get_by_placeholder("0").fill("100")
        await page.locator("#numPadContainerView").get_by_role("button", name="Next").click()


        await page.get_by_test_id("selection-list-text-input").fill("testuser@gmail.com")
        await page.get_by_test_id('selection-list').locator('button[tabindex="0"]').click()
        await page.get_by_role("button", name=re.compile(r"Submit [\\w$€£¥]+")).click()
        await page.wait_for_timeout(2000)


        view_details = page.get_by_label("View details")
        await view_details.wait_for()
        await view_details.click()
        await page.wait_for_timeout(1000)
        await page.get_by_role("textbox").click()
        await page.get_by_role("textbox").fill("1")
        await page.get_by_role("textbox").press("Enter")
        await page.get_by_role("textbox").click()
        await page.get_by_role("textbox").fill("2")
        await page.get_by_role("textbox").press("Enter")


        await page.get_by_role('button').locator('svg[width="12"][height="12"]').click()
        await page.get_by_text("Delete expense").click()
        await page.get_by_role("button", name="Delete").click()


        await page.wait_for_timeout(2000)
        assert not await page.get_by_test_id("ReportDetailsPage").is_visible(), f"Expected Report Details Page to be closed"



        await page.get_by_label("Start chat (Floating action)").click()
        await page.get_by_text("Submit expense").first.click()
        await page.get_by_placeholder("0").fill("200")
        await page.locator("#numPadContainerView").get_by_role("button", name="Next").click()
        await page.get_by_test_id("selection-list-text-input").fill("testuser1@gmail.com")
        await page.get_by_label("testuser1@gmail.com").click()
        await page.get_by_role("button", name=re.compile(r"Submit [\\w$€£¥]+")).click()


        await page.locator('button[aria-label="Create"]').last.click()
        await page.get_by_text("Submit expense").click()
        await page.get_by_placeholder("0").fill("300")
        await page.locator("#numPadContainerView").get_by_role("button", name="Next").click()
        await page.get_by_role("button", name=re.compile(r"Submit [\\w$€£¥]+")).click()


        await view_details.wait_for()
        await view_details.click()
        await page.get_by_text("Cash").first.click()
        await page.get_by_role("textbox").click()
        await page.get_by_role("textbox").fill("1")
        await page.get_by_role("textbox").press("Enter")
        await page.get_by_role("textbox").click()
        await page.get_by_role("textbox").fill("2")
        await page.get_by_role("textbox").press("Enter")


        await page.get_by_label(re.compile(r".*300\\.00 expense")).last.click()
        await page.get_by_text("Delete expense").click()
        await page.get_by_role("button", name="Delete").click()


        await page.wait_for_timeout(2000)
        assert not await page.get_by_test_id("ReportDetailsPage").is_visible(), f"Expected Report Details Page to be closed"

    finally:

        await context.tracing.stop(path=trace_path)
        trace_cleaner(trace_path)
        await close_browser(context, page, playwright)
