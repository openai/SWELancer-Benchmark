import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import pytest
from playwright.async_api import expect, async_playwright
from playwright._impl._page import Page
from utils.login import sign_up, complete_onboarding
from utils.browser import close_browser
from utils.email_handler import get_specific_derived_email

BASE_EMAIL = 'testuserexpensify@gmail.com'
PROXY_SERVER = 'http://127.0.0.1:8080'

async def start_browser_with_proxy():
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(
        slow_mo=500,
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
async def test_delete_expense_with_comments():
    from utils.trace_cleaner import trace_cleaner
    trace_path = "/app/expensify/user_tool/output_browser1.zip"

    # Set up the email to use for the test
    derived_email = get_specific_derived_email(BASE_EMAIL, '549312')

    # Start browser
    context, page, playwright = await start_browser_with_proxy()
    
    try:
        # Start tracing
        await context.tracing.start(screenshots=True, snapshots=True, sources=True)

        # Step 1: Login / Sign up
        await sign_up(page, derived_email)

        # Complete onboarding
        try:
            await complete_onboarding(page, first_name='Jane', last_name='Doe')
        except Exception:
            pass

        # Check if the Inbox is visible
        await expect(page.get_by_label("Inbox")).to_be_visible()
        await page.locator('button[aria-label="Navigates to a chat"]', has_text='Jane Doe').click()

        # Step 2: Select appropriate message area for testing
        message_editor = page.locator('div[contenteditable="true"][placeholder="Write something..."]').last

        # Step 3: Send a normal single backtick code block message ("`Hello`")
        await message_editor.fill("`Hello`")
        await message_editor.press("Enter")
        await page.wait_for_timeout(2000)
        # Assert the font-size is 13px for the normal single backtick message
        await expect(page.locator("span:has-text('Hello')")).to_have_css("font-size", "13px")

        # Step 4: Send a bold single backtick code block message ("# `Hello world`")
        await message_editor.fill("# `Hello world`")
        await message_editor.press("Enter")
        await page.wait_for_timeout(2000)

        # Assert the font-size is 15px for the bold single backtick message
        await expect(page.locator("span:has-text('Hello world')")).to_have_css("font-size", "15px")

    except Exception as e:
        # Reraise after capturing trace
        raise e
    finally:
        # Stop tracing and save trace to file
        await context.tracing.stop(path=trace_path)
        # Clean the trace
        trace_cleaner(trace_path)
        # Close browser
        await close_browser(context, page, playwright)
