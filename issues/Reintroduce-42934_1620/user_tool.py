import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time

import pytest
from playwright.async_api import async_playwright

EMAIL = "testexpensifyturing+009@gmail.com"
PASSWORD = "qqdd pegp kagr emax"

NEW_DOT_URL = "https://example.com"

@pytest.mark.asyncio
async def test_issue_42934():
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(
        headless=True,
        args=["--disable-web-security", "--disable-features=IsolateOrigins, site-per-process"],
        proxy={"server": "127.0.0.1:8080"}
    )
    device = playwright.devices['iPhone 15']
    context = await browser.new_context(**device, ignore_https_errors=True)
    page = await context.new_page()

    try:
        # Start tracing
        await context.tracing.start(
            title="test_issue_42934",
            snapshots=True,
            screenshots=True
        )
        
        await page.goto(NEW_DOT_URL)

        # Login user
        await page.get_by_test_id("username").fill(EMAIL)
        await page.get_by_role("button", name="Continue").click()
        await page.get_by_test_id("validateCode").fill("123456")

        # Create workspace
        await page.get_by_label("My settings").click()
        await page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()
        await page.wait_for_timeout(1000)
        await page.get_by_test_id("WorkspacesListPage").get_by_label("New workspace").first.click()

        # Go to inbox
        await page.get_by_test_id("WorkspaceInitialPage").get_by_label("Back").click()
        await page.wait_for_timeout(500)
        await page.get_by_test_id("WorkspacesListPage").get_by_label("Back").click()
        await page.locator('button[aria-label="Inbox"]').click()
        await page.wait_for_timeout(2000)

        # Navigate into the chat
        await page.get_by_label("Navigates to a chat").last.click()

        # Create Task
        await page.get_by_label("Create").click()
        await page.get_by_text("Assign task").click()
        await page.get_by_role("textbox", name="Title").click()
        await page.get_by_role("textbox", name="Title").fill("past")
        await page.get_by_role("button", name="Next").click()
        await page.get_by_role("button", name="Confirm task").click()
        await page.wait_for_timeout(2000)

        # Step 3: Get the checkbox bounding box for alignment verification
        checkbox = page.get_by_role("checkbox", name="Task")
        checkbox_box = await checkbox.bounding_box()

        # Step 4: Assert that the vertical center of the checkbox is aligned as expected
        assert checkbox_box["y"] + checkbox_box["height"] / 2 == 552
        
    finally:
        # Stop tracing and save it
        await context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
        
        # Clean the trace
        from utils.trace_cleaner import trace_cleaner
        trace_cleaner("/app/expensify/user_tool/output_browser1.zip")

        # Close browser
        await page.close()
        await context.close()
        await playwright.stop()
