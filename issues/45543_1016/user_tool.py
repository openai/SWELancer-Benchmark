import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from utils.trace_cleaner import trace_cleaner

import pytest
from playwright.async_api import expect, async_playwright, Browser, Page
from utils.login import sign_in, NEW_DOT_URL, check_if_logged_in
from utils.browser import close_browser


USER_EMAILA = "doorsqueaky+3182311@gmail.com"
USERNAME_A = 'John Doe'
PASSWORD_A = "eabcahqraatorpvt"
USER_EMAILB = "windowsqueaky+3919211@gmail.com"
PASSWORD_B = "jeaqzqklzxxdetsh"
USERNAME_B = 'Jane Doe'


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
    # Start tracing for this context
    await context.tracing.start(screenshots=True, snapshots=True, sources=True)
    page = await context.new_page()
    return context, page, playwright


async def send_message(page: Page, recepient_email: str, message: str):

    await page.locator('button[aria-label="Start chat (Floating action)"]').click()
    await page.locator('div[aria-label="Start chat"][role="menuitem"]').click()


    await page.locator('input[aria-label="Name, email, or phone number"]').fill(recepient_email)
    await page.get_by_test_id('selection-list').locator(f'button:has-text("{recepient_email}")').click()
    await page.wait_for_timeout(1000)


    message_editor = page.locator('div[contenteditable="true"][placeholder="Write something..."]').last
    await message_editor.fill(message)
    await message_editor.press("Enter")


async def create_draft_reply_in_thread(page: Page, username: str, sender_email: str, message: str, reply: str):

    if await page.locator('button[aria-label="Navigates to a chat"]', has_text=sender_email).is_visible():
        await page.locator('button[aria-label="Navigates to a chat"]', has_text=sender_email).click()
    else:
        await page.locator('button[aria-label="Navigates to a chat"]', has_text=username).click()


    await page.locator('div[aria-label="Chat message"]', has_text=message).click(button="right")
    await page.locator('div[aria-label="Reply in thread"][role="menuitem"]').click()

    await page.wait_for_timeout(1000)


    message_editor = page.locator('div[aria-label="Chat message"]', has_text=message)
    # Assuming the draft editor is the same as the message editor for reply
    message_editor = page.locator('div[contenteditable="true"][placeholder="Write something..."]').last
    await message_editor.fill(reply)


async def navigate_away_check_draft(page: Page, username: str, sender_email: str):

    if await page.locator('button[aria-label="Navigates to a chat"]', has_text=sender_email).is_visible():
        await page.locator('button[aria-label="Navigates to a chat"]', has_text=sender_email).click()
    else:
        await page.locator('button[aria-label="Navigates to a chat"]', has_text=username).click()


    await page.wait_for_timeout(2000)


    draft_reply_LHN_btn = page.locator('button[aria-label="Navigates to a chat"]', has_text="No activity yet")
    await expect(draft_reply_LHN_btn).to_be_visible()


async def enter_dummy_otp_if_not_logged_in(page: Page, email: str):
    if not await check_if_logged_in(page=page, url=NEW_DOT_URL):
        await page.get_by_test_id("username").fill(email)
        await page.get_by_role("button", name="Continue").click()
        await page.get_by_test_id("validateCode").fill("123456")


@pytest.mark.asyncio
async def test_workspace_switch_on_reload():
    # Initialize browser contexts to None for cleanup
    contextA = contextB = None
    pageA = pageB = None
    playwrightA = playwrightB = None

    try:
        contextA, pageA, playwrightA = await start_browser_with_proxy()

        await enter_dummy_otp_if_not_logged_in(pageA, USER_EMAILA)

        await expect(pageA.get_by_label("Inbox")).to_be_visible()

        message = "Hello How are you"
        await send_message(pageA, USER_EMAILB, message)

        contextB, pageB, playwrightB = await start_browser_with_proxy()

        await enter_dummy_otp_if_not_logged_in(pageB, USER_EMAILB)

        await expect(pageA.get_by_label("Inbox")).to_be_visible()

        reply = "Hey I am good. What about you?"
        await create_draft_reply_in_thread(pageB, USERNAME_A, USER_EMAILA, message, reply)
        await navigate_away_check_draft(pageB, USERNAME_A, USER_EMAILA)

    finally:
        # Stop tracing and export the trace before closing each browser
        if contextA is not None:
            await contextA.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            await close_browser(contextA, pageA, playwrightA)
        if contextB is not None:
            await contextB.tracing.stop(path="/app/expensify/user_tool/output_browser2.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser2.zip")
            await close_browser(contextB, pageB, playwrightB)