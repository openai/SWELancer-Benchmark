import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import pytest
from playwright.async_api import expect, async_playwright
from utils.login import sign_in, check_if_logged_in, NEW_DOT_URL
from utils.browser import close_browser


USER_EMAIL = "testuserexpensify+2941212@gmail.com"
PASSWORD = "wcgrsdxlmzvuekxd"

async def start_browser_with_proxy():
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
    context = await browser.new_context(ignore_https_errors=True)
    page = await context.new_page()
    return context, page, playwright


# Test function
@pytest.mark.asyncio
async def test_issue_41433():
    # Start browser
    context, page, playwright = await start_browser_with_proxy()

    # Step 1: sign in
    if not await check_if_logged_in(page=page, url=NEW_DOT_URL):
        await page.get_by_test_id("username").fill(USER_EMAIL)
        await page.get_by_role("button", name="Continue").click()
        await page.get_by_test_id("validateCode").fill("123456")

    # Step 2: check if self DM is visible
    self_dm = page.get_by_test_id('lhn-options-list').get_by_text('John Doe')
    await expect(self_dm).to_be_visible()
    await self_dm.click()

    # Step 3: enter the text by simulating the space and abc keyboard
    textbox = page.get_by_role("textbox")
    await textbox.click()
    await textbox.press("Space")
    await textbox.type("abc")

    # Step 4: click on Send and select the emoji
    await page.get_by_label("Send").last.click()
    await page.get_by_label("Emoji").locator("path").last.click()
    await page.get_by_label("😀").first.click()

    # Step 5: verify that the emoji is preselected and selected.
    target_text = "😀 "
    selected_text = await page.evaluate("""
        () => {
            const selection = window.getSelection();
            return selection.toString();  // Get the selected text
        }
    """)

    assert selected_text != target_text, "The emoji is Preselected, This should not have happened!!"

    # Close browser
    await close_browser(context, page, playwright)