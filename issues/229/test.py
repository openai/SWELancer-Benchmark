import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.async_api import (
    async_playwright,
    expect,
    Page,
    Browser,
    PlaywrightContextManager,
)
import re
import pytest

EMAIL = "expensify66+543209565435065432247@gmail.com"
FIRST_NAME = "Milan"
LAST_NAME = "Tonborn"


async def simulate_netsuite_fail(page: Page, workspace_id: str):

    js_code = """
    async (workspace_id) => {
        const net_suite = {
            lastSync: {
            errorDate: "2024-12-9T10:26:57+0000",
            errorMessage: "Unable to validate NetSuite tokens",
            isAuthenticationError: true,
            isConnected: false,
            isSuccessful: false,
            source: "NEWEXPENSIFY",
            successfulDate: "",
            },
            verified: false,
        };

        await Onyx.merge(`policy_${workspace_id}`, {
            connections: {
            netsuite: net_suite,
            },
        });
    };
    """

    await page.evaluate(js_code, workspace_id)


async def login_user(
    p: PlaywrightContextManager, first_name="Milan", last_name="T"
) -> tuple[Browser, Page, str]:

    browser = await p.chromium.launch(
        headless=True,
        args=[
            "--ignore-certificate-errors",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
        ],
        proxy={"server": "http://127.0.0.1:8080"},
        slow_mo=500,
    )
    page: Page = await browser.new_page()


    await page.goto("https://dev.new.expensify.com:8082/")


    await page.get_by_test_id("username").fill(EMAIL)
    await page.get_by_role("button", name="Continue").click()


    await page.get_by_role("button", name="Join").click()


    await page.locator("text=What do you want to do today?").wait_for(timeout=5000)

    await page.locator("text='Track and budget expenses'").click()
    await page.get_by_role("button", name="Continue").click()


    await page.locator('input[name="fname"]').fill(first_name)
    await page.locator('input[name="lname"]').fill(last_name)
    await page.get_by_role("button", name="Continue").last.click()
    await page.get_by_text("Get Started").click(timeout=3000)

    return browser, page


async def create_workspace_and_enable_netsuite(page: Page) -> str:
    """
    Create a new workspace and enable netsuite
    """


    await page.get_by_label("My settings").click()
    await page.get_by_text("Workspaces").last.click()
    await page.get_by_text("New workspace").first.click()


    await page.get_by_test_id("WorkspaceInitialPage").get_by_text(
        "More features"
    ).click()
    workspace_id = re.search(r"settings/workspaces/([^/]+)/", page.url).group(1)
    await page.get_by_label("Sync your chart of accounts").click()
    await page.get_by_test_id("WorkspaceInitialPage").get_by_text(
        "Accounting"
    ).click()


    await page.get_by_label("NetSuite").get_by_role(
        "button", name="Connect"
    ).click()
    await page.get_by_role("button", name="Upgrade").click(timeout=3000)
    await page.get_by_role("button", name="Got it, thanks").click()
    await page.get_by_test_id("NetSuiteTokenInputPage").get_by_label("Back").click()

    return workspace_id


@pytest.mark.asyncio
async def test_first_issue_error_message() -> None:

    async with async_playwright() as p:

        browser, page = await login_user(p, FIRST_NAME, LAST_NAME)


        workspace_id = await create_workspace_and_enable_netsuite(page)


        await simulate_netsuite_fail(page, workspace_id)


        await expect(
            page.get_by_test_id("PolicyAccountingPage").get_by_text(
                "Can't connect to NetSuite"
            ),
            "Error message is not visible",
        ).to_be_visible(timeout=10000)

        await browser.close()
