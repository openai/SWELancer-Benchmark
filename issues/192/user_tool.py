import os
import random
import string

import pytest
from playwright.async_api import Browser, Page, TimeoutError, async_playwright
from utils.trace_cleaner import trace_cleaner

WORKSPACE_NAME = "pyPtFh23"
EMAIL_USERNAME = "xecuycismfsga"
EMAIL_ALIAS = "kj56jrdw"
USER_EMAIL = f"{EMAIL_USERNAME}+{EMAIL_ALIAS}@gmail.com"
PASSWORD = ""
SLOW_MO: int | None = 500
PROXY_URL = os.getenv("PROXY_URL")


def generate_random_string(length=6):
    letters_and_digits = string.ascii_letters + string.digits
    return "".join(random.choice(letters_and_digits) for _ in range(length))


 def generate_random_email(alias: str = generate_random_string()):
    return f"{EMAIL_USERNAME}+{alias}@gmail.com"


async def get_magic_code(
    _page: Page, _user_email: str = USER_EMAIL, _password: str = PASSWORD
):
    return "123456"


async def create_user(page: Page, firstname: str = "User", lastname: str = EMAIL_ALIAS):
    await page.get_by_role("button", name="Join").click()

    # Update profile
    await page.get_by_text("Track and budget expenses").click()
    await page.get_by_role("textbox", name="First name").fill(firstname)
    await page.get_by_role("textbox", name="Last name").fill(lastname)
    await page.get_by_role("button", name="Continue").click()


async def login(page: Page):
    # get current timestamp
    magic_code = await get_magic_code(page)

    if magic_code is None:
        raise ValueError("Failed to retrieve magic code")

    await page.get_by_role("textbox").fill(magic_code)


async def login_or_create_user(
    page: Page,
    last_name: str = EMAIL_ALIAS,
    user_email: str = USER_EMAIL,
):
    await page.goto("https://dev.new.expensify.com:8082/")
    await page.get_by_test_id("username").fill(user_email)
    await page.get_by_role("button", name="Continue").click()

    try:
        await page.get_by_role("button", name="Join").wait_for(
            state="visible", timeout=2000
        )
        await create_user(page, last_name)
    except TimeoutError:
        await login(page)

    await page.get_by_label("Inbox").wait_for(state="visible", timeout=10000)


async def create_workspace(page: Page, workspace_name: str = WORKSPACE_NAME):
    """
    Create a workspace if it does not already exist
    """
    await page.get_by_label("My Settings").click()
    await page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()

    try:
        await (
            page.locator('button[aria-label="row"]')
            .filter(has_text=workspace_name)
            .last.click(timeout=3000)
        )
    except TimeoutError:
        await page.get_by_label("New workspace").last.click()

        await page.get_by_text("Name", exact=True).click()
        name_input = page.get_by_role("textbox", name="Name")
        await name_input.clear()
        await name_input.type(workspace_name, delay=200)
        await page.get_by_role("button", name="Save").click()


async def setup_workspace(browser: Browser):
    admin_context = await browser.new_context(
        permissions=["clipboard-read", "clipboard-write"]
    )
    # Start tracing for admin context
    await admin_context.tracing.start(screenshots=True, snapshots=True, sources=True)
    admin_page = await admin_context.new_page()

    await login_or_create_user(admin_page)

    await create_workspace(admin_page)

    await admin_page.get_by_role("button", name="Share").click()
    await admin_page.get_by_label("Copy URL").click()
    await admin_page.wait_for_timeout(1000)  # wait for clipboard to be populated
    workspace_url = await admin_page.evaluate("navigator.clipboard.readText()")
    return workspace_url, admin_context


@pytest.mark.asyncio(scope="session")
async def test_workspace_access():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            proxy={"server": PROXY_URL} if PROXY_URL else None,
            headless=False,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--ignore-certificate-errors",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
            ],
            slow_mo=SLOW_MO,
            channel="chromium",
        )
        # Setup workspace using admin context and start its tracing above
        workspace_url, admin_context = await setup_workspace(browser)

        # Create a new context for the restricted user
        context = await browser.new_context()
        # Start tracing for the restricted user context
        await context.tracing.start(screenshots=True, snapshots=True, sources=True)
        page = await context.new_page()

        # Wrap the main test logic in try/finally to ensure tracing stops and trace exported
        try:
            restricted_user_alias = generate_random_string()
            restricted_user_email = generate_random_email(restricted_user_alias)

            await login_or_create_user(
                page, user_email=restricted_user_email, last_name=restricted_user_alias
            )

            await page.goto(workspace_url)

            await (
                page.locator('button[aria-label="row"]')
                .filter(has_text=WORKSPACE_NAME)
                .last.wait_for(state="visible", timeout=10000)
            )
        finally:
            # Stop tracing and export trace for restricted user context
            restricted_trace_path = "/app/expensify/user_tool/output_browser2.zip"
            await context.tracing.stop(path=restricted_trace_path)
            trace_cleaner(restricted_trace_path)
            await page.close()
            await context.close()
            
            # Stop tracing and export trace for admin context
            admin_trace_path = "/app/expensify/user_tool/output_browser1.zip"
            # Retrieve the admin page from admin_context if needed before stopping tracing
            await admin_context.tracing.stop(path=admin_trace_path)
            trace_cleaner(admin_trace_path)
            await admin_context.close()
            
            # Close the browser after all tracing exports
            await browser.close()