import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import pytest

from playwright.async_api import (
    async_playwright,
    expect,
    Browser,
    BrowserContext,
    Page,
    PlaywrightContextManager,
)

EXPENSIFY = "https://dev.new.expensify.com:8082/"

EMAIL = "doorsqueaky+9652421543554321425655453@gmail.com"

USER_FNAME = "Manisha"
USER_LNAME = "Reddy"


async def launch_browser(
    p: PlaywrightContextManager,
) -> tuple[Browser, BrowserContext, Page]:
    """
    Launches a new browser and opens a new page
    """
    browser = await p.chromium.launch(
        headless=True,
        args=[
            "--ignore-certificate-errors",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
        ],
    )
    context = await browser.new_context()
    page = await context.new_page()

    return browser, context, page


async def duplicate_tab(context: BrowserContext, page_a: Page):
    """
    Duplicates a given tab (page)
    """
    storage_state = await context.storage_state()

    page_b = await context.new_page()
    await context.add_cookies(storage_state["cookies"])
    await page_b.goto(page_a.url)

    return page_b


async def login_newdot(page: Page, user_email: str, first_name: str, last_name: str):
    """
    Creates a new account for a user in NewDot
    """

    await page.goto(EXPENSIFY)

    await page.get_by_test_id("username").fill(user_email)
    await page.get_by_role("button", name="Continue").click()

    await page.get_by_role("button", name="Join").click()


    await page.get_by_text("Track and budget expenses").click()
    await page.get_by_role("button", name="Continue").click()


    await page.locator('input[name="fname"]').fill(first_name)
    await page.locator('input[name="lname"]').fill(last_name)
    await page.get_by_role("button", name="Continue").last.click()

    await page.get_by_label("guided-setup-track-personal-").wait_for()


async def create_new_workspace(page: Page):
    """
    Creates a new workspace
    """

    await page.get_by_label("My settings").click()


    await page.locator('div[aria-label="Workspaces"][role="menuitem"]').click()
    await page.locator('button[aria-label="New workspace"]').first.click()


async def tax_feature_toggle(page: Page, toggle_value: bool):
    """
    Enables/Disables Tax feature for the workspace
    """

    await page.get_by_test_id("WorkspaceInitialPage").get_by_label(
        "More features"
    ).click()
    tax_toggle_button = page.get_by_label("Document and reclaim eligible taxes.")
    checked = await tax_toggle_button.get_attribute("aria-checked")
    if (checked == "true" and toggle_value == False) or (
        checked == "false" and toggle_value == True
    ):
        await tax_toggle_button.click()


async def check_back_button_navigation(page: Page):
    """
    Check if the back button on not found page navigates to WS editor/details page
    """

    not_found_message = page.locator("span", has_text="Oops, this page cannot be found")
    await expect(not_found_message).to_be_visible()


    await page.get_by_test_id("NotFoundPage").get_by_label("Back").click()


    await expect(
        page.get_by_test_id("WorkspaceInitialPage").get_by_label("Profile")
    ).to_be_visible()
    await expect(
        page.get_by_test_id("WorkspaceInitialPage").get_by_label("Members")
    ).to_be_visible()
    await expect(
        page.get_by_test_id("WorkspaceInitialPage").get_by_label("Categories")
    ).to_be_visible()
    await expect(
        page.get_by_test_id("WorkspaceInitialPage").get_by_label("More features")
    ).to_be_visible()


@pytest.mark.asyncio
async def test_back_button_navigation():
    """
    Tests if back button press navigates to WS
    editor/details page
    """
    async with async_playwright() as pw:

        browser, context, page_a = await launch_browser(pw)


        await login_newdot(page_a, EMAIL, USER_FNAME, USER_LNAME)


        await create_new_workspace(page_a)

        await tax_feature_toggle(page_a, True)
        await page_a.get_by_test_id("WorkspaceInitialPage").get_by_label(
            "Taxes"
        ).click()


        page_b = await duplicate_tab(context, page_a)
        await tax_feature_toggle(page_b, False)


        await page_a.bring_to_front()
        await check_back_button_navigation(page_a)

        await browser.close()
