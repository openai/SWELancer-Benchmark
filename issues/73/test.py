import os
import random
import string

import pytest
from playwright.async_api import Page, TimeoutError, async_playwright, expect

EMAIL_USERNAME = "xecuycismfsga"
EMAIL_ALIAS = "vuha2kun"
USER_EMAIL = f"{EMAIL_USERNAME}+{EMAIL_ALIAS}@gmail.com"
PASSWORD = "uwgb zzoc cofa kaaq"
SLOW_MO: int | None = 500
PROXY_URL = os.getenv("PROXY_URL")
WORKSPACE_NAME = "5jvnxtxT"


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
            .last.click(timeout=3000)
        )
    except TimeoutError:
        await page.get_by_label("New workspace").last.click()

        await (
            page.get_by_test_id("WorkspacePageWithSections")
            .get_by_text("Workspace name", exact=True)
            .click()
        )
        name_input = page.get_by_role("textbox", name="Name")
        await name_input.clear()
        await name_input.type(workspace_name, delay=200)
        await page.get_by_role("button", name="Save").click()


def generate_random_string(length: int = 8) -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def generate_random_number(minimum=1, maximum=1000):
    return random.randint(minimum, maximum)


async def submit_expense(page: Page, workspace_name: str = WORKSPACE_NAME):
    workspace_chat = (
        page.get_by_text("Submit expenses using your workspace chat below:")
        .locator("xpath=following-sibling::div[1]")
        .get_by_label(workspace_name)
    )
    await workspace_chat.click()

    await page.get_by_label("Create").last.click()
    await page.get_by_text("Submit expense", exact=True).click()
    await page.get_by_label("Manual").click()
    await page.get_by_placeholder("0").fill(str(generate_random_number()))
    await (
        page.locator("#numPadContainerView").get_by_role("button", name="Next").click()
    )
    await page.get_by_label("Show more").click()
    await page.get_by_text("Tax exempt (0%)").wait_for(state="visible", timeout=3000)

    await page.get_by_role("menuitem", name="Category").click()
    await page.get_by_label("Advertising").click()
    await expect(page.get_by_text("Tax Rate A (5.5%)")).to_be_visible()


async def close_button_if_present(page: Page):
    """
    Occasionally, there is a close button that prevents any clicks on the page as
    it covers most of the screen. This button cannot be seen visually.
    """
    close_button = page.locator('button[aria-label="Close"]')
    if await close_button.is_visible():
        await close_button.click()


async def enable_rules(page: Page):
    await page.get_by_label("More features").click()
    rules = page.get_by_label("Require receipts, flag high spend, and more.")
    if not await rules.is_checked():
        await rules.click()

    try:
        await page.get_by_role("button", name="Upgrade").click(timeout=3000)
        await page.get_by_role("button", name="Got it, thanks").click()
    except TimeoutError:
        pass


async def enable_taxes(page: Page):
    await page.get_by_label("More features").click()
    taxes = page.get_by_role("switch", name="Document and reclaim eligible")

    if not await taxes.is_checked():
        await taxes.click()


def generate_locator_id(name: str) -> str:
    # Remove any leading/trailing whitespace and replace internal spaces with underscores
    cleaned_name = name.strip().replace(" ", "_")
    # Convert to uppercase
    return f"#id_{cleaned_name.upper()}"


async def add_tax_rate(page: Page, name: str, amount: float):
    try:
        await page.locator(generate_locator_id(name)).wait_for(
            state="visible", timeout=2000
        )
    except TimeoutError:
        await page.get_by_role("button", name="Add rate").click()
        await page.get_by_role("menuitem", name="Name Required").click()
        await page.get_by_role("textbox", name="Name").fill(name)
        await (
            page.get_by_test_id("TextSelectorModal")
            .get_by_role("button", name="Save")
            .click()
        )
        await page.get_by_role("menuitem", name="Value Required").click()
        await page.get_by_role("textbox", name="0").fill(str(amount))
        await (
            page.get_by_test_id("AmountSelectorModal")
            .get_by_role("button", name="Save")
            .click()
        )
        await page.get_by_role("button", name="Save").click()


async def add_new_tax_rates(page: Page):
    await page.get_by_role("menuitem", name="Taxes").click()

    rates = {"Tax Rate A": 5.5, "Tax Rate B": 7.2}

    for name, amount in rates.items():
        await add_tax_rate(page, name, amount)


async def add_rate_to_category(page: Page):
    await page.get_by_role("menuitem", name="Categories").click()

    await page.locator("#Advertising").click()
    await page.get_by_text("Default tax rate").click()
    await page.get_by_role("button", name="Tax Rate A • 5.5%").click()
    await (
        page.get_by_test_id("CategorySettingsPage")
        .get_by_role("button", name="Back")
        .click()
    )


@pytest.mark.asyncio(scope="session")
async def test_scroll_to_comments():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            proxy={"server": "http://localhost:8080"},
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
        context = await browser.new_context()
        page = await context.new_page()

        # admin login
        await login_or_create_user(page)
        await close_button_if_present(page)

        await create_workspace(page)

        await enable_rules(page)
        await enable_taxes(page)
        await add_new_tax_rates(page)
        await add_rate_to_category(page)

        await submit_expense(page)

        # Close all tabs and browser
        await page.close()
        await context.close()
        await browser.close()
