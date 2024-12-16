import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import pytest
from utils.login import sign_up, complete_onboarding
from utils.browser import close_browser
from playwright.async_api import expect, async_playwright

from utils.trace_cleaner import trace_cleaner

PROXY_SERVER = 'http://127.0.0.1:8080'

async def start_browser_with_proxy():
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(
        slow_mo=650,
        headless=True,
        proxy={
            'server': PROXY_SERVER
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
async def test_leave_chat_thread():
    derived_email = "testuserexpensify+9574131@gmail.com"

    context, page, playwright = await start_browser_with_proxy()

    # Start tracing
    await context.tracing.start(
        title="test_leave_chat_thread",
        screenshots=True,
        snapshots=True,
        sources=True
    )

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

        # Step 2: Create a chat group
        await page.get_by_label("Start chat (Floating action)").click()
        await page.get_by_text("Start chat").click()
        await page.get_by_test_id("selection-list-text-input").fill("testuser@gmail.com")
        await page.wait_for_timeout(2000)
        await page.get_by_role("button", name="Add to group").click()
        await page.get_by_test_id("selection-list-text-input").click()
        await page.get_by_test_id("selection-list-text-input").fill("testuser1@gmail.com")
        await page.wait_for_timeout(2000)
        await page.get_by_role("button", name="Add to group").click()
        await page.get_by_role("button", name="Next").click()
        await page.get_by_role("button", name="Start group").click()

        # Step 3: Start a message thread
        await page.get_by_role("textbox").click()
        await page.get_by_role("textbox").fill("Message A")
        await page.get_by_role("button", name="Send").click()
        await page.locator("span").filter(has_text="Message A").click(button="right")
        await page.get_by_text("Reply in thread").click()
        await page.get_by_role("textbox").fill("Message B")
        await page.get_by_role("button", name="Send").click()

        await page.wait_for_timeout(2000)
        # Step 4: open the message thread
        await page.locator(
            'div[data-testid="DisplayNamesWithTooltip"]', has_text="Message A"
        ).last.click()

        # Assert that the "Leave" button is not visible on the details page of a thread
        await expect(page.get_by_text("Leave")).not_to_be_visible()

    except Exception as e:
        # Re-raise any exception so the test fails
        raise e
    finally:
        # Ensure that trace is always stopped and cleaned up
        await context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
        trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
        await close_browser(context, page, playwright)
