import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import pytest

from utils.login import NEW_DOT_URL, check_if_logged_in
from utils.browser import start_browser, close_browser
from playwright.async_api import expect


EMAIL = "brighturing926+50465@gmail.com"


@pytest.mark.asyncio
async def test_issue_50465() -> None:
    newWorkspceName1 = "taxdisablepagews823"
    context, page, playwright = await start_browser(
        launch_args=["--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins, site-per-process"]
    )

    # Step 1: Sign in
    if await check_if_logged_in(page=page, url=NEW_DOT_URL) == False:
        await page.get_by_test_id("username").fill(EMAIL)
        await page.get_by_role("button", name="Continue").click()
        my_otp = "123456"
        await page.get_by_test_id("validateCode").fill(my_otp)

    # Step 3: Disable Taxes
    await page.get_by_label("My settings").click()
    await page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()
    await page.wait_for_timeout(2000)

    await page.get_by_text(newWorkspceName1, exact=True).last.click()

    await page.get_by_label("More features").click()

    await page.get_by_label("Document and reclaim eligible").click()
    await page.get_by_test_id("WorkspaceInitialPage").get_by_label("Taxes").click()

    page1 = await context.new_page()
    await page1.goto(page.url)
    await page1.get_by_label("More features").click()
    await page1.get_by_label("Document and reclaim eligible").click()

    # Step 4: Go back the error page
    await page.wait_for_timeout(2000)
    try:
        await page.get_by_test_id("NotFoundPage").get_by_label("Back").click()
    except Exception:
        # In case the first tab doesn't show the Not Found page, we can force an update by clicking on More Features and then instantly switching back
        # to the Taxes tab.
        await page.get_by_label("More features").click()
        await page.get_by_test_id("WorkspaceInitialPage").get_by_label("Taxes").click()
        await page.get_by_test_id("NotFoundPage").get_by_label("Back").click()
    workspace_list = page.get_by_test_id("WorkspacesListPage").get_by_text("Workspaces")

    await expect(workspace_list).not_to_be_visible()
    await close_browser(context, page, playwright)