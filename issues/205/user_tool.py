import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import pytest
import logging

from utils.login import NEW_DOT_URL, check_if_logged_in
from utils.browser import start_browser, close_browser
from utils.trace_cleaner import trace_cleaner
from playwright.async_api import expect

logging.basicConfig(level=logging.INFO)

EMAIL = "brighturing926+50357@gmail.com"

@pytest.mark.asyncio
async def test_issue_50357():
    newWorkspceName = "qbocredentialws262634"
    context, page, playwright = await start_browser(
        launch_args=["--disable-web-security", "--disable-features=IsolateOrigins, site-per-process"]
    )


    await context.tracing.start(
        title="test_issue_50357",
        screenshots=True,
        snapshots=True,
        sources=True
    )

    try:

        if await check_if_logged_in(page=page, url=NEW_DOT_URL) == False:
            await page.get_by_test_id("username").fill(EMAIL)
            await page.get_by_role("button", name="Continue").click()
            await page.get_by_test_id("validateCode").fill("123456")

        await page.get_by_label("My settings").click()
        await page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()
        await page.wait_for_timeout(2000)
        await page.get_by_text(newWorkspceName, exact=True).last.click()

        await page.get_by_test_id("WorkspaceInitialPage").get_by_text("Accounting").click()


        await page.get_by_test_id("PolicyAccountingPage").get_by_label("More").click()
        await page.wait_for_timeout(3000)
        enter_credentials = page.get_by_label("Enter your Credentials")

        await expect(enter_credentials).to_be_visible()

    except Exception as e:

        raise e

    finally:

        trace_path = "/app/expensify/user_tool/output_browser1.zip"
        await context.tracing.stop(path=trace_path)
        trace_cleaner(trace_path)


        await close_browser(context, page, playwright)
