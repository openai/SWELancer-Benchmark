import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import pytest

from utils.login import NEW_DOT_URL, check_if_logged_in
from utils.browser import start_browser, close_browser
from utils.trace_cleaner import trace_cleaner
# from playwright.async_api import expect

USER_EMAIL = "brighturing926+4577@gmail.com"
WORKSPACE_NAME = "multitagsws142"


@pytest.mark.asyncio
async def test_edit_dependent_tags() -> None:
    context = None
    page = None
    playwright = None

    try:
        context, page, playwright = await start_browser(
            launch_args=["--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins, site-per-process"]
        )

        # Start tracing
        await context.tracing.start(
            title="test_edit_dependent_tags",
            screenshots=True,
            snapshots=True,
            sources=True
        )

        # Step 1: Sign in
        if await check_if_logged_in(page=page, url=NEW_DOT_URL) == False:
            await page.get_by_test_id("username").fill(USER_EMAIL)
            await page.get_by_role("button", name="Continue").click()
            otp_code = "123456"
            await page.get_by_test_id("validateCode").fill(otp_code)

        # Create New Workspace
        await page.get_by_label("My settings").click()
        await page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()
        await page.get_by_text(WORKSPACE_NAME, exact=True).last.click()
        await page.wait_for_timeout(2000)

        # verify you can edit the state GL
        await page.get_by_test_id("WorkspaceInitialPage").get_by_label("Tags").click()
        await page.get_by_label("State").click()
        await page.locator("#California").click()
        await page.get_by_test_id("TagSettingsPage").get_by_text("GL code").click()
        try:
            # Since it's a static workspace and tags, clear anything in the field first
            await page.get_by_role("textbox", name="GL code").fill("")
            await page.get_by_role("button", name="Save").click()
            await page.get_by_test_id("TagSettingsPage").get_by_text("GL code").click()
        except Exception:
            pass
        await page.get_by_role("textbox", name="GL code").fill("1001")
        await page.get_by_role("button", name="Save").click()
        await page.wait_for_timeout(1000)
        await page.get_by_test_id("TagSettingsPage").get_by_text("GL code").click()
        val = await page.get_by_role("textbox", name="GL code").input_value()
        assert val == "1001", "Value should be updated"

    except Exception as e:
        # Test has failed, but we still want to record and clean the trace
        print(f"Test failed with error: {e}")
        raise

    finally:
        if context:
            # Stop tracing and save
            await context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
        if context and page and playwright:
            # Close browser
            await close_browser(context, page, playwright)
