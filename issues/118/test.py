import os
import random
import re
import string

import pytest
from playwright.async_api import Page, TimeoutError, async_playwright

EMAIL_USERNAME = "xecuycismfsga"
EMAIL_ALIAS = "6nvqaqhy"
USER_EMAIL = f"{EMAIL_USERNAME}+{EMAIL_ALIAS}@gmail.com"
PASSWORD = ""
SLOW_MO: int | None = 500
PROXY_URL = os.getenv("PROXY_URL")


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


async def create_workspace(page: Page, workspace_name: str):
    """
    Create a workspace if it does not already exist
    """
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


async def submit_expense(page: Page, workspace_name: str):
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
    await page.get_by_text("Merchant").click()
    await page.get_by_role("textbox", name="Merchant").last.fill(
        generate_random_string()
    )
    await page.get_by_role("button", name="Save").click()
    await page.get_by_role("button", name="Submit").click()


async def close_button_if_present(page: Page):
    """
    Occasionally, there is a close button that prevents any clicks on the page as
    it covers most of the screen. This button cannot be seen visually.
    """
    close_button = page.locator('button[aria-label="Close"]')
    if await close_button.is_visible():
        await close_button.click()


async def delete_workspaces(page: Page):
    await page.get_by_label("My settings").click()
    await page.get_by_role("menuitem", name="Workspaces").click()
    # Loop until no more rows are found
    while True:
        row = (
            page.get_by_test_id("WorkspacesListPage")
            .locator('button[aria-label="row"]')
            .filter(has=page.locator('button[aria-label="More"]'))
        )

        if await row.count() == 0:
            break  # Exit loop when no more rows with "More" button are found

        await row.last.get_by_label("More").click()

        await page.get_by_label("Delete workspace").click()
        await page.get_by_role("button", name="Delete").click()


async def pay_elsewhere(page: Page, workspace_name: str):
    expense_preview = page.get_by_role("button", name="View details").filter(
        has_text=f"{workspace_name} owes:"
    )
    await expense_preview.click()

    try:
        await page.get_by_role("button", name="Got it").click(timeout=2000)
    except TimeoutError:
        pass

    await (
        page.get_by_role("button", name="Pay")
        .locator("xpath=../following-sibling::*[1]")
        .click()
    )
    await page.get_by_role("menuitem", name="elsewhere").click()
    await page.get_by_role("button", name=re.compile(r".* elsewhere")).click()

    try:
        await page.get_by_role("button", name="Pay").last.click(timeout=2000)
    except TimeoutError:
        pass


async def cancel_payment(page: Page, workspace_name: str):
    payment_details = page.locator(
        f'div[data-testid="DisplayNamesWithTooltip"]:has-text("{workspace_name} paid")'
    ).last
    await payment_details.click()

    await page.get_by_role("menuitem", name="Cancel payment").click()
    await page.get_by_role("button", name="Cancel payment").click()


async def assert_scroll_to_comments(page: Page):
    messages = page.get_by_label("List of chat messages").last
    scroll_top = await messages.evaluate("el => el.scrollTop")
    assert scroll_top == 0, "Last message is not visible; didn't scroll"


async def send_messages(page: Page):
    for message in [f"Message {i}" for i in range(7)]:
        await page.get_by_placeholder("Write something...").last.fill(message)
        await page.get_by_role("button", name="Send").click()

    messages = page.get_by_label("List of chat messages").last
    await messages.evaluate(
        "el => el.scrollTop = 1000;"
    )  # scroll to the top of the container


@pytest.mark.asyncio(scope='session')
async def test_scroll_to_comments():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            proxy = {"server": "http://localhost:8080"}, headless = False, args = ["--no-sandbox", "--disable-dev-shm-usage", "--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"], slow_mo = SLOW_MO, channel = "chromium")

        context = await browser.new_context()
        page = await context.new_page()

        # admin login
        await login_or_create_user(page)
        await close_button_if_present(page)

        await delete_workspaces(page)
        workspace_name = "SdiPDTAc"  # replay workspace_name is hardcoded
        # workspace_name = generate_random_string()
        await create_workspace(page, workspace_name)

        await submit_expense(page, workspace_name)
        await pay_elsewhere(page, workspace_name)

        await send_messages(page)

        await cancel_payment(page, workspace_name)

        await page.wait_for_timeout(5000)  # wait for notification event to propagate

        await assert_scroll_to_comments(page)

        # Close all tabs and browser
        await page.close()
        await context.close()
        await browser.close()
