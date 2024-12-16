import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time

import pytest
from playwright.async_api import expect

from utils.browser import start_browser, close_browser
from utils.login import check_if_logged_in, NEW_DOT_URL, sign_in

EMAIL = "testexpensifyturing+006@gmail.com"
PASSWORD = "qqdd pegp kagr emax"


@pytest.mark.asyncio
async def test_issue_49894():
    # Start browser
    context, page, playwright = await start_browser(
        persistent=True,
        launch_args=["--disable-web-security", "--disable-features=IsolateOrigins, site-per-process"],
    )

    # Sign in
    # Not using the utility function here since we don't need a valid OTP when running the test with the recorded flow.
    # Any random OTP works
    if not await check_if_logged_in(page=page, url=NEW_DOT_URL):
        await page.get_by_test_id("username").fill(EMAIL)
        await page.get_by_role("button", name="Continue").click()
        await page.get_by_test_id("validateCode").fill("123456")

    # Start Room Chat
    await page.get_by_label("Start chat (Floating action)").click()
    await page.get_by_text("Start chat").click()
    await page.get_by_label("Room", exact=True).click()
    await page.get_by_placeholder("social").fill(f"room{int(time.time())}")
    await page.get_by_role("textbox", name="Room description (optional)").fill("`  `")
    await page.get_by_role("button", name="Create room").click()
    await page.wait_for_timeout(500)

    # Assign task and set title and empty description
    await page.get_by_role("button", name="Create").click()
    await page.get_by_label("Assign task").click()
    await page.get_by_role("textbox", name="Title").fill("title1")
    await page.get_by_role("button", name="Next").click()

    # Edit description and type "` `"
    await page.get_by_test_id("NewTaskPage").get_by_text("Description").click()
    await page.get_by_role("textbox", name="Description (optional)").fill("` `")
    await page.get_by_role("button", name="Next").click()

    # Check if this is in markdown
    await expect(page.get_by_test_id("NewTaskPage").locator('span')).to_have_text(" ")

    # Open description and add a space
    await page.get_by_test_id("NewTaskPage").get_by_text("Description").click()
    await page.wait_for_timeout(1000)
    await page.get_by_role("textbox", name="Description (optional)").fill("` ` ")
    await page.get_by_role("button", name="Next").click()

    # Check if this is still in markdown
    await page.wait_for_timeout(500)
    await expect(page.get_by_test_id("NewTaskPage").locator('span')).to_have_count(1)
    await expect(page.get_by_test_id("NewTaskPage").locator('span')).to_have_text(" ")

    # Close the browser
    await close_browser(context, page, playwright)