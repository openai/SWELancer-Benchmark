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
        slow_mo=800,
        headless=True,
        proxy={
            'server': PROXY_SERVER
        },
        args=[
            '--ignore-certificate-errors',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process'
        ]
    )
    desktop = playwright.devices['Desktop Chrome']
    desktop["viewport"] = {"width": 375, "height": 667}
    context = await browser.new_context(
        ignore_https_errors=True,
        **desktop
    )
    page = await context.new_page()
    return context, page, playwright


async def create_account(page: Page, email: str):
    # Step 1: Login / Sign up
    await sign_up(page, email)

    # Complete onboarding
    try:
        await complete_onboarding(page)
    except Exception:
        pass

    await page.wait_for_timeout(2000)
    if await page.locator('button:has-text("Get started")').is_visible():
        await page.locator('button:has-text("Get started")').click()

    # Check if the Inbox is visible
    await expect(page.get_by_label("Inbox")).to_be_visible()


# Test function
@pytest.mark.asyncio
async def test_list_of_chats():
    try:
        context, page, playwright = await start_browser_with_proxy()
        user_email = get_specific_derived_email(BASE_EMAIL, '67652121')
        await create_account(page, user_email)
        await page.get_by_label("Back").last.click()
        await page.get_by_label("Close").click()
        await page.locator('div[aria-label="Chat pinned"]').last.click()
        await page.get_by_label("Create").click()
        await page.get_by_text("Assign task").click()
        await page.get_by_role("textbox", name="Title").click()
        await page.get_by_role("textbox", name="Title").fill("asdf")
        await page.get_by_role("button", name="Next").click()
        await page.get_by_role("button", name="Confirm task").click()
        await page.locator('button[aria-label="Task"]').last.click()
        await page.locator('div[data-testid="DisplayNamesWithTooltip"]',has_text="asdf").last.click()
        await page.get_by_text("Delete").last.click()
        await page.get_by_text("Delete").last.click()
        await page.get_by_label("Back").last.click()
        deleted_chat = page.locator('div', has_text="[Deleted task]").last
        await expect(deleted_chat).not_to_be_visible()
        list_of_chats = page.get_by_label("List of chats").last
        await page.wait_for_timeout(2000)
        await expect(list_of_chats).to_be_visible()
    finally:
        await close_browser(context, page, playwright)