import pytest
from playwright.async_api import Page, expect
from utils.login import NEW_DOT_URL, sign_in
from utils.browser import close_browser, start_browser
from utils.trace_cleaner import trace_cleaner


STATIC_PREFIX = 55073
EXPENSIFY_USERNAME_FIRSTNAME = "osaidtest"
EXPENSIFY_USERNAME_LASTNAME = "testaccount"
EXPENSIFY_USERNAME = f"{EXPENSIFY_USERNAME_FIRSTNAME} {EXPENSIFY_USERNAME_LASTNAME}"
EXPENSIFY_EMAIL_USERNAME = "osaidtest5"
EXPENSIFY_EMAIL = f"osaidtest5+{STATIC_PREFIX}@gmail.com"
EXPENSIFY_PASSWORD = "ntvd acej mmaa qqmd"
DATA_DIR = "browser_context"
WORKSPACE_NAME = "workspace_1"
SLOW_MO = 1000
NORMAL_RUN = False
PROXY_SETTINGS = {"server": "http://localhost:8080"}


async def sign_in_recorded(page: Page, email: str):
    await page.get_by_test_id("username").fill(email)
    await page.get_by_role("button", name="Continue").click()
    await page.get_by_test_id("validateCode").fill("123456")


@pytest.mark.asyncio
async def test_41157():
    context, page, playwright = await start_browser(
        persistent=False,
        data_dir=DATA_DIR,
        headless=False,
        slow_mo=SLOW_MO,
        launch_args=[
            "--ignore-certificate-errors",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
        ],
        proxy=PROXY_SETTINGS
    )

    # Start tracing
    await context.tracing.start(screenshots=True, snapshots=True, sources=True)

    try:
        # Step 1: Sign in
        if NORMAL_RUN:
            # Normal test run
            await sign_in(page, EXPENSIFY_EMAIL, password=EXPENSIFY_PASSWORD)
        else:
            # Recorded Test Run.
            await page.goto(NEW_DOT_URL)
            await sign_in_recorded(page=page, email=EXPENSIFY_EMAIL)

        # Go to the workspace settings.
        await page.get_by_role("button", name="My settings").click()
        await page.get_by_role("menuitem", name="Workspaces").click()
        await page.get_by_test_id("WorkspacesListPage").get_by_role(
            "button", name="row"
        ).filter(has=page.get_by_text(WORKSPACE_NAME)).click()
        await page.get_by_role('menuitem', name='Workflows').click()
        await page.get_by_text("Connect bank account").click()
        await page.get_by_role("menuitem", name="State").click()
        await page.get_by_test_id("selection-list-text-input").fill("randominput")
        await page.get_by_test_id("PushRowModal").get_by_label("Back").click()
        await page.get_by_role("menuitem", name="State").click()
        await expect(page.get_by_test_id("selection-list-text-input")).not_to_have_value('randominput')
    finally:
        # Stop tracing and export the trace file
        trace_path = "/app/expensify/user_tool/output_browser1.zip"
        await context.tracing.stop(path=trace_path)
        trace_cleaner(trace_path)
        # Close the browser
        await close_browser(context, page, playwright)