import csv
import os

import pytest
from playwright.async_api import (
    BrowserContext,
    Page,
    TimeoutError,
    async_playwright,
    expect,
)

EMAIL_USERNAME = "xecuycismfsga"
EMAIL_ALIAS = "v1pmabnf"
USER_EMAIL = f"{EMAIL_USERNAME}+{EMAIL_ALIAS}@gmail.com"
PASSWORD = "uwgb zzoc cofa kaaq"
SLOW_MO: int | None = 500
PROXY_URL = os.getenv("PROXY_URL")
WORKSPACE_NAME = "5jvnxtxT"
FILENAME = "tags_import.csv"
WORKSPACE_NAME = "vSRAAJ6t"
OLD_DOT_URL = "http://127.0.0.1:9000/"

EMPLOYEE_ALIAS = "zpt4gjv4"
EMPLOYEE_EMAIL = f"{EMAIL_USERNAME}+{EMPLOYEE_ALIAS}@gmail.com"


def create_spreadsheet(filename=FILENAME):
    # Write CSV
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["State", "State GL", "Region", "Region GL", "City", "City GL"])

        # Define hierarchical structure
        states = {
            "California": {
                "GL": 100,
                "regions": {
                    "North": {
                        "GL": 20,
                        "cities": [("San Francisco", 1), ("Oakland", 2)],
                    },
                    "South": {
                        "GL": 30,
                        "cities": [("Los Angeles", 3), ("San Diego", 4)],
                    },
                },
            },
        }

        for state, state_data in states.items():
            for region, region_data in state_data["regions"].items():
                for city, city_gl in region_data["cities"]:
                    writer.writerow(
                        [
                            state,
                            state_data["GL"],
                            region,
                            region_data["GL"],
                            city,
                            city_gl,
                        ]
                    )
    return filename


async def login_user_old_dot(page, user_email=USER_EMAIL):
    await page.goto(OLD_DOT_URL)
    try:
        await page.locator('div[id="js_modalClose"]').click(timeout=2000)
    except TimeoutError:
        pass

    await page.get_by_role("button", name="Sign In").click()
    await page.get_by_role("button", name="Email ").click()
    await page.get_by_placeholder("Enter your email to begin").fill(user_email)
    await page.get_by_role("button", name="Next").click()

    if await page.get_by_text("We are having trouble connecting.").is_visible():
        print("Try a different IP address with a VPN")
        return

    magic_code = await get_magic_code(page)
    await page.get_by_placeholder("Magic Code").fill(magic_code)
    await page.locator("#js_click_signIn").click()
    await page.wait_for_timeout(
        3000
    )  # Waiting to make sure that the request was sent to the backend
    await page.goto(f"{OLD_DOT_URL}inbox")


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


async def open_tags(page: Page):
    tags = page.get_by_label("Tags")
    try:
        await tags.wait_for(state="visible", timeout=2000)
    except TimeoutError:
        await page.get_by_label("More features").click()
        await page.get_by_label("Classify costs and track").click()  # enable tags

    await tags.click()


def get_test_dir():
    try:
        test_dir = os.path.dirname(os.path.abspath(__file__))
    except NameError:  # We're in a notebook
        test_dir = os.getcwd()

    return test_dir


async def upload_tags(page: Page, context: BrowserContext):
    try:
        await page.get_by_role("button", name="State").wait_for(
            state="visible", timeout=2000
        )
        await page.get_by_role("button", name="Region").wait_for(
            state="visible", timeout=2000
        )
        await page.get_by_role("button", name="City").wait_for(
            state="visible", timeout=2000
        )
    except TimeoutError:
        old_dot_page = await context.new_page()
        await login_user_old_dot(old_dot_page)

        # Define the relative path to the text file
        filename = create_spreadsheet()
        script_dir = get_test_dir()
        image_file_path = os.path.join(script_dir, filename)

        old_dot_page.on(
            "filechooser", lambda file_chooser: file_chooser.set_files(image_file_path)
        )

        await old_dot_page.get_by_role("link", name=" Settings").click()
        await old_dot_page.get_by_role("link", name=" Settings").click()
        await old_dot_page.locator("#page_admin_policies").click()
        await (
            old_dot_page.locator("a").filter(has_text="Group").click()
        )  # group policies
        await old_dot_page.get_by_role("link", name=WORKSPACE_NAME).click()
        await old_dot_page.get_by_role("link", name="Tags").click()
        await (
            old_dot_page.locator("li")
            .filter(has_text="Use multiple levels of")
            .locator("label")
            .nth(1)
            .click()
        )
        await old_dot_page.get_by_role("button", name="Import from Spreadsheet").click()
        await old_dot_page.get_by_label("Are these independent tags?").uncheck()
        await old_dot_page.get_by_label("Is there a GL code in the").check()
        await old_dot_page.get_by_role("button", name="Select File").first.click(
            force=True
        )
        await old_dot_page.get_by_role("button", name="Upload Tags").click()


async def get_magic_code(
    page: Page, user_email: str = EMAIL_USERNAME, password: str = PASSWORD
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
    await page.goto("https://dev.new.expensify.com:8082/", timeout=60000)
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


async def create_expense(page: Page, workspace_name: str = WORKSPACE_NAME):
    await page.locator(
        'button[aria-label="Navigates to a chat"]',
        has_text=workspace_name,
    ).first.click()

    await page.get_by_label("Create").last.click()
    await page.get_by_label("Create expense").click()
    await page.get_by_label("Manual").click()
    await page.get_by_placeholder("0").fill("100")
    await (
        page.locator("#numPadContainerView").get_by_role("button", name="Next").click()
    )
    await expect(page.get_by_text("California")).to_be_visible()


async def close_button_if_present(page: Page):
    """
    Occasionally, there is a close button that prevents any clicks on the page as
    it covers most of the screen. This button cannot be seen visually.
    """
    close_button = page.locator('button[aria-label="Close"]')
    if await close_button.is_visible():
        await close_button.click()


async def invite_member_to_workspace(
    page: Page,
    user_email: str = EMPLOYEE_EMAIL,
    name: str = f"User {EMPLOYEE_ALIAS}",
):
    await page.get_by_label("Members").click()

    member_locator = (
        page.get_by_test_id("WorkspaceMembersPage").get_by_label(name).first
    )

    try:
        await member_locator.wait_for(state="visible", timeout=3000)
    except TimeoutError:
        await page.get_by_role("button", name="Invite member").click()

        await page.get_by_test_id("selection-list-text-input").fill(user_email)
        await page.get_by_test_id("selection-list").get_by_label(name).first.click()

        await page.get_by_role("button", name="Next").click()

        await (
            page.get_by_test_id("WorkspaceInviteMessagePage")
            .get_by_role("button", name="Invite")
            .click()
        )


async def logout(page: Page):
    await page.get_by_label("My settings").click()
    await page.get_by_label("Sign out").click()


@pytest.mark.asyncio
async def test_prefill_state():
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
        context = await browser.new_context()
        page = await context.new_page()

        # admin login
        await login_or_create_user(page)
        await close_button_if_present(page)

        employee_context = await browser.new_context()
        employee_page = await employee_context.new_page()

        await login_or_create_user(
            employee_page, user_email=EMPLOYEE_EMAIL, lastname=EMPLOYEE_ALIAS
        )

        await create_workspace(page)
        await invite_member_to_workspace(page)
        await open_tags(page)
        await upload_tags(page, context)

        await create_expense(employee_page)

        # Close all tabs and browser
        await page.close()
        await employee_page.close()
        await context.close()
        await employee_context.close()
        await browser.close()
