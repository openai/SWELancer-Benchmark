import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import pytest

from utils.login import NEW_DOT_URL, check_if_logged_in
from utils.browser import start_browser, close_browser
from playwright.async_api import expect


EMAIL = "brighturing926+49543@gmail.com"


@pytest.mark.asyncio
async def test_issue_49543() -> None:
    workspace_name = "multitagsws45"
    context, page, playwright = await start_browser(
        launch_args=["--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins, site-per-process"]
    )

    # Step 1: Sign in
    if await check_if_logged_in(page=page, url=NEW_DOT_URL) == False:
        await page.get_by_test_id("username").fill(EMAIL)
        await page.get_by_role("button", name="Continue").click()
        my_otp = "123456"
        await page.get_by_test_id("validateCode").fill(my_otp)

    await page.get_by_label("My settings").click()
    await page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()
    await page.wait_for_timeout(2000)
    await page.get_by_text(workspace_name, exact=True).last.click()

    await page.wait_for_timeout(3000)
    await page.get_by_test_id("WorkspaceInitialPage").get_by_label("Tags").click()
    await page.get_by_label("State").click()
    await page.locator("#California").click()

    # Validate the absence of the "Tag rules" feature
    tag_rules_element = page.get_by_text("Tag rules")

    await expect(tag_rules_element).not_to_be_visible()

    # Close the browser
    await close_browser(context, page, playwright)
