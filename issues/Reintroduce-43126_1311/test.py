import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import re
import pytest
from utils.login import sign_up, complete_onboarding
from utils.browser import start_browser, close_browser
from playwright.async_api import expect, async_playwright
from playwright._impl._page import Page


# Test function
@pytest.mark.asyncio
async def test_leave_chat_thread():
    derived_email = "testuserexpensify+967441130@gmail.com"

    # Start browser
    context, page, playwright = await start_browser(launch_args=[
        '--disable-web-security',
        '--disable-features=IsolateOrigins,site-per-process'
    ])

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

    # Step 4: open the message thread
    await page.get_by_label("Message a").click()
    # Assert that the "Leave" button is not visible on the details page pof a thread
    await expect(page.get_by_text("Leave")).not_to_be_visible()

    # ---------------------
    await close_browser(context, page, playwright)