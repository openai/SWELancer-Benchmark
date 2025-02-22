import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import random
import pytest

from utils.login import NEW_DOT_URL, check_if_logged_in
from utils.browser import start_browser, close_browser
from playwright.async_api import expect


EMAIL = "brighturing926+49894@gmail.com"


@pytest.mark.asyncio
async def test_issue_49894() -> None:
    random_num = random.randint(111, 9999)
    code_block_room = f"cdbk{random_num}"
    context, page, playwright = await start_browser(
        launch_args=["--disable-web-security", "--disable-features=IsolateOrigins, site-per-process"]
    )


    if await check_if_logged_in(page=page, url=NEW_DOT_URL) == False:
        await page.get_by_test_id("username").fill(EMAIL)
        await page.get_by_role("button", name="Continue").click()
        await page.get_by_test_id("validateCode").fill("123456")


    await page.locator('button[aria-label="Start chat (Floating action)"]').click()


    await page.locator('div[role="menuitem"]:has-text("Start chat")').click()


    await page.locator('button[aria-label="Room"]').click()


    await page.locator('input[aria-label="Room name"]').fill(code_block_room)


    await page.locator('button:has-text("Create room")').click()


    await page.locator('button[aria-label="Create"]').last.click()


    await page.locator('div[role="menuitem"]:has-text("Assign task")').click()


    await page.locator('input[aria-label="Title"]').fill("testTask")


    description_input = page.locator('div[aria-label="Description (optional)"]').last
    await description_input.fill("")  # Clear the input field
    await description_input.fill("`    `")  # Enter the new description


    await page.locator('button:has-text("Next")').click()


    await page.locator('button[aria-label="Back"][role="button"]').last.click()


    await page.locator('button:has-text("Next")').click()


    nbsp_block = page.locator('div[data-testid="code"] span.css-textHasAncestor-1jxf684')


    await expect(nbsp_block).to_be_visible()


    await close_browser(context, page, playwright)
