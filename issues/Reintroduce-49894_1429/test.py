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

    # Step 1: Sign in
    if await check_if_logged_in(page=page, url=NEW_DOT_URL) == False:
        await page.get_by_test_id("username").fill(EMAIL)
        await page.get_by_role("button", name="Continue").click()
        await page.get_by_test_id("validateCode").fill("123456")

    # Step 1: Click on "+" icon
    await page.locator('button[aria-label="Start chat (Floating action)"]').click()

    # Step 2: Click on the "Start Chat" button in the opened report
    await page.locator('div[role="menuitem"]:has-text("Start chat")').click()

    # Step 3: Click on the "Room" button
    await page.locator('button[aria-label="Room"]').click()

    # Step 4: Enter the room name
    await page.locator('input[aria-label="Room name"]').fill(code_block_room)

    # Step 5: Click on "Create room" button
    await page.locator('button:has-text("Create room")').click()

    # Step 6: Click on the plus button
    await page.locator('button[aria-label="Create"]').last.click()

    # Step 7: Click on "Assign task" button
    await page.locator('div[role="menuitem"]:has-text("Assign task")').click()

    # Step 8: Enter the title
    await page.locator('input[aria-label="Title"]').fill("testTask")

    # Step 9: Clear the description input field and then enter the description
    description_input = page.locator('div[aria-label="Description (optional)"]').last
    await description_input.fill("")  # Clear the input field
    await description_input.fill("`    `")  # Enter the new description

    # Step 10: Click "Next" button
    await page.locator('button:has-text("Next")').click()

    # Step 11: Click "Back" button
    await page.locator('button[aria-label="Back"][role="button"]').last.click()

    # Step 12: Click "Next" button again
    await page.locator('button:has-text("Next")').click()

    # Refined locator for the specific element
    nbsp_block = page.locator('div[data-testid="code"] span.css-textHasAncestor-1jxf684')

    # Check visibility
    await expect(nbsp_block).to_be_visible()

    # Step 5: Close the browser
    await close_browser(context, page, playwright)