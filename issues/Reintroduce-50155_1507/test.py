import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
import pytest

from utils.login import NEW_DOT_URL, check_if_logged_in
from utils.browser import start_browser, close_browser
from playwright.async_api import expect


EMAIL = "brighturing926+50155@gmail.com"


@pytest.mark.asyncio
async def test_issue_50155():
    context, page, playwright = await start_browser(
        launch_args=["--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins, site-per-process"]
    )

    # Step 1: Sign in
    if await check_if_logged_in(page=page, url=NEW_DOT_URL) == False:
        await page.get_by_test_id("username").fill(EMAIL)
        await page.get_by_role("button", name="Continue").click()
        await page.get_by_test_id("validateCode").fill("123456")

    # Step 2: Go to one on one chat
    await page.get_by_label("Start chat (Floating action)").click()
    await page.get_by_label("Start chat", exact=True).click()
    random = int(time.time())
    await page.get_by_test_id("selection-list-text-input").fill(f"teststs{random}@gmail.com")
    await page.get_by_label(f"teststs{random}@gmail.com").click()

    # Step 3: Select book travel
    await page.get_by_label("Start chat (Floating action)").click()
    await page.get_by_label("Book travel").click()
    await page.get_by_label("Book travel").click()

    # Step 4: Select country and go back to overlay and check that say hello is visible
    await page.get_by_role("menuitem", name="Country").click()
    await page.locator("#overLayBottomButton").click()

    try:
        await expect(page.get_by_text("Say hello!", exact=True).nth(1)).to_be_visible()
    except Exception:
        await expect(page.get_by_text("Say hello!", exact=True).first).to_be_visible()

    # Step 5: Close the browser
    await close_browser(context, page, playwright)