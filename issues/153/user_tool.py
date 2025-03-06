import os
import random
import re
import string

import pytest
from playwright.async_api import Page, TimeoutError, async_playwright, expect
from utils.trace_cleaner import trace_cleaner

<<<<<<< HEAD
# Utility function to generate a unique random email for testing
def generate_random_email():
    timestamp = int(time.time())
    return f"t1533148+{timestamp}@gmail.com"

EMAIL = "t1533148@gmail.com"  # for example test+1234@gmail.com
PASSWORD = ""  # it will be something like "sdib pxop ovyl uawy"
=======
EMAIL_USERNAME = "xecuycismfsga"
EMAIL_ALIAS = "kypqxmbx"
USER_EMAIL = f"{EMAIL_USERNAME}+{EMAIL_ALIAS}@gmail.com"
PASSWORD = "uwgb zzoc cofa kaaq"
SLOW_MO: int | None = 500
PROXY_URL = os.getenv("PROXY_URL")

WORKSPACE_NAME = "BltGot0t"
>>>>>>> main


async def create_workspace(page: Page, workspace_name: str = WORKSPACE_NAME):
    """
    Create a workspace if it does not already exist
    """
    await page.get_by_label("My settings").click()
    await page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()

    try:
        await (
            page.locator('button[aria-label="row"]')
            .filter(has_text=workspace_name)
            .last.wait_for(timeout=3000)
        )
    except TimeoutError:
        await page.get_by_label("New workspace").last.click()

        await page.get_by_text("Name", exact=True).click()
        name_input = page.get_by_role("textbox", name="Name")
        await name_input.clear()
        await name_input.type(workspace_name, delay=200)
        await page.get_by_role("button", name="Save").click()
        await (
            page.get_by_test_id("WorkspaceInitialPage")
            .get_by_label("Back")
            .first.click()
        )

    await page.get_by_label("Inbox").click()


def generate_random_string(length=6, case="mixed"):
    if case == "lower":
        characters = string.ascii_lowercase
    elif case == "upper":
        characters = string.ascii_uppercase
    elif case == "mixed":
        characters = string.ascii_letters
    else:
        raise ValueError("Case must be 'lower', 'upper', or 'mixed'")

    random_string = "".join(random.choice(characters) for _ in range(length))
    return random_string


async def get_magic_code(
    page: Page, user_email: str = USER_EMAIL, password: str = PASSWORD
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
    firstname: str = "User",
    lastname: str = EMAIL_ALIAS,
    user_email: str = USER_EMAIL,
):
    await page.goto("https://dev.new.expensify.com:8082/")
    await page.get_by_test_id("username").fill(user_email)
    await page.get_by_role("button", name="Continue").click()

    try:
        await page.get_by_role("button", name="Join").wait_for(
            state="visible", timeout=2000
        )
        await create_user(page, firstname=firstname, lastname=lastname)
    except TimeoutError:
        await login(page)

    await page.get_by_label("Inbox").wait_for(state="visible", timeout=10000)


async def submit_expense(page: Page):
    expense_preview = (
        page.get_by_role("button", name="View details")
        .filter(has_text=f"{WORKSPACE_NAME} owes:")
        .last
    )

    try:
        await expense_preview.wait_for(state="visible", timeout=3000)
    except TimeoutError:
        await page.get_by_label("Create").last.click()
        await page.get_by_text("Submit expense", exact=True).click()
        await page.get_by_label("Manual").click()
        await page.get_by_placeholder("0").fill("100")
        await (
            page.locator("#numPadContainerView")
            .get_by_role("button", name="Next")
            .click()
        )
        await page.get_by_text("Merchant").click()
        await page.get_by_role("textbox", name="Merchant").fill("test")
        await page.get_by_role("button", name="Save").click()
        await page.get_by_role("button", name="Submit").click()

    return expense_preview


async def enable_custom_fields_and_rules(page: Page):
    await page.get_by_label("My settings").click()
    await page.get_by_role("menuitem", name="Workspaces").click()

    await (
        page.locator('button[aria-label="row"]')
        .filter(has_text=WORKSPACE_NAME)
        .last.click(timeout=3000)
    )

    await page.get_by_label("More features").click()
    custom_fields = page.get_by_label("Set up custom fields for spend.")

    if not await custom_fields.is_checked():
        await custom_fields.click()

    try:
        await page.get_by_role("button", name="Upgrade").click(timeout=3000)
        await page.get_by_role("button", name="Got it, thanks").click()
    except TimeoutError:
        pass

    rules = page.get_by_label("Require receipts, flag high spend, and more.")
    if not await rules.is_checked():
        await rules.click()


<<<<<<< HEAD
# Test to verify opening distance receipt from another workspace opens without issue
def test_open_receipt_different_workspace():
    with sync_playwright() as p:
        browser, context, page, user_email1 = login_user(p)
        # Start tracing with screenshots, snapshots, and sources
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        trace_file = "/app/expensify/user_tool/output_browser1.zip"
=======
async def add_custom_report_name(page: Page):
    await page.get_by_role("menuitem", name="Rules").click()
    custom_report_names = page.get_by_role(
        "switch", name="Custom report names", exact=True
    )
    if not await custom_report_names.is_checked():
        await custom_report_names.click()

    await page.get_by_role("menuitem", name="report", exact=True).click()
    await page.locator('input[aria-label="Name"]').fill("report")
    await page.get_by_role("button", name="Save").click()


@pytest.mark.asyncio
async def test_search_bar_spacing():
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
        )

        context = await browser.new_context()
        await context.tracing.start(screenshots=True, snapshots=True, sources=True)
        page = await context.new_page()

>>>>>>> main
        try:
            await login_or_create_user(page)
            await create_workspace(page)

            workspace_chat = (
                page.locator(
                    'button[aria-label="Navigates to a chat"]',
                    has_text=WORKSPACE_NAME,
                )
                .filter(has_not_text="#admins")
                .first
            )
            await workspace_chat.click()

            expense_preview = await submit_expense(page)
            await expense_preview.click()

            await enable_custom_fields_and_rules(page)
            await add_custom_report_name(page)

            await (
                page.get_by_test_id("WorkspaceInitialPage")
                .get_by_label("Back")
                .first.click()
            )
            await page.get_by_label("Inbox").click()

            report_details = (
                page.locator('div[data-testid="DisplayNamesWithTooltip"]')
                .filter(has_text=re.compile(r"Expense Report #\d+"))
                .last
            )
            report_title = await report_details.inner_text(timeout=5000)

            await page.get_by_text("Title").last.click()
            await page.locator('input[aria-label="Title"]').fill(generate_random_string())
            await page.get_by_role("button", name="Save").click()

            await expect(
                page.locator('div[data-testid="DisplayNamesWithTooltip"]')
                .filter(has_text=report_title)
                .last
            ).to_be_visible()

            # Close all tabs gracefully
            await page.close()
            await context.close()
        finally:
            # Ensure tracing is stopped and trace is exported even if an error occurs
            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            await context.tracing.stop(path=trace_path)
            trace_cleaner(trace_path)
            await browser.close()