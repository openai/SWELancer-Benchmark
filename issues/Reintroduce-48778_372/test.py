import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

"""
The test assumes a manually created workspace with the approvers set up on 2 levels
The expense is also created manually to avoid duplicates and any unforseen issues
Hence the test basically assumes the role of the second approver and checks that the "Submit" exists or not
"""
from playwright._impl._page import Page

import pytest

from utils.login import NEW_DOT_URL, check_if_logged_in
from utils.browser import start_browser, close_browser
from playwright.async_api import expect


EMAIL = "brighturing926+311@gmail.com"
EMAIL1 = "brighturing926+313@gmail.com"
EMAIL2 = "brighturing926+314@gmail.com"
workspace_name = "zilmultiapprover23"


@pytest.mark.asyncio
async def test_issue_48778() -> None:
    context, page, playwright = await start_browser(
        launch_args=[
            "--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins, site-per-process"]
    )

    # Step 1: Sign in
    if await check_if_logged_in(page=page, url=NEW_DOT_URL) == False:
        await page.get_by_test_id("username").fill(EMAIL)
        await page.get_by_role("button", name="Continue").click()
        my_otp = "123456"
        await page.get_by_test_id("validateCode").fill(my_otp)

        submitter_fname, submitter_lname = await get_names_for_existing_account(page)

    # Setup 1st and 2nd approvers with delay
    await page.get_by_label("My settings").click()
    await page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()
    await page.get_by_text(workspace_name, exact=True).last.click()

    await page.get_by_label("Back").click()
    await page.get_by_label("Inbox").click()
    await page.locator('div[data-testid="lhn-options-list"]').get_by_text(workspace_name).first.click()

    # Submit expense
    amount = str(1)
    merchant = "G"

    #######################################################################
    # As the approver 2, navigate to the submitter's workspace chat
    #######################################################################
    # Second Aprover
    context2, page2, playwright2 = await start_browser(
        launch_args=[
            "--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins, site-per-process"]
    )
    if await check_if_logged_in(page=page2, url=NEW_DOT_URL) == False:
        await page2.get_by_test_id("username").fill(EMAIL2)
        await page2.get_by_role("button", name="Continue").click()
        my_otp = "123456"
        await page2.get_by_test_id("validateCode").fill(my_otp)
        approver2_fname, approver2_lname = await get_names_for_existing_account(page2)
    await page2.get_by_label("Inbox").click()
    await page2.get_by_test_id("CustomBottomTabNavigator").get_by_label("Search").click()

    _button_label = f"{merchant} {submitter_fname} {submitter_lname} {approver2_fname} {approver2_lname} ${amount}.00 View"
    await page2.get_by_role("button", name=_button_label).click()

    await page2.wait_for_timeout(5000)

    ####################################################################################################
    # Step 8: Verify that the 'submit' button should NOT be visible to second-level+ non-admin approvers.
    #####################################################################################################

    await expect(page2.get_by_role("button", name="Submit", exact=True)).not_to_be_visible()

    await close_browser(context, page, playwright)
    await close_browser(context2, page2, playwright2)


async def get_names_for_existing_account(page: Page) -> tuple[str, str]:
    """
    Retrive first and last name from the account profile
    """
    await page.get_by_label("My settings").click()
    try:
        await page.get_by_label("Close").click(timeout=1000)
    except Exception:
        pass
    await page.get_by_role("menuitem", name="Profile").click()
    await page.get_by_text("Display name").last.click()
    f_name = await page.get_by_role("textbox", name="First name").input_value()
    l_name = await page.get_by_role("textbox", name="Last name").input_value()
    await page.wait_for_timeout(2000)
    await page.keyboard.down("Escape")

    return f_name, l_name
