import os
import random
import re
import string

import pytest
from playwright.async_api import Page, TimeoutError, async_playwright

EMAIL_USERNAME = "xecuycismfsga"
EMAIL_ALIAS = "l3rb8ruz"
USER_EMAIL = f"{EMAIL_USERNAME}+{EMAIL_ALIAS}@gmail.com"
PASSWORD = "uwgb zzoc cofa kaaq"
SLOW_MO: int | None = 500
PROXY_URL = os.getenv("PROXY_URL")


def generate_random_string(length=6, case="lower"):
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

        iphone = p.devices["iPhone 14"]
        context = await browser.new_context(**iphone)
        page = await context.new_page()

        email_alias = generate_random_string()
        user_email = f"{EMAIL_USERNAME}+{email_alias}@gmail.com"

        await login_or_create_user(page, lastname=email_alias, user_email=user_email)

        try:
            # Navigate back to LHN if inside Concierge chat
            await page.get_by_text(
                "Hey there, I'm Concierge! If you have any"
            ).wait_for(state="visible", timeout=2000)
            await page.get_by_label("Back").first.click()
        except TimeoutError:
            pass

        await page.get_by_label("Start chat (Floating action)").click()
        await page.get_by_label("New workspace").click()
        await page.go_back()

        workspace_name = re.compile(r"User .*'s Workspace")
        workspace_chat_button = page.locator(
            'button[aria-label="Navigates to a chat"]', has_text=workspace_name
        )

        await workspace_chat_button.wait_for(state="visible", timeout=3000)
        workspace_box = await workspace_chat_button.bounding_box()

        assert (
            workspace_box is not None
        ), f"Workspace chat button with text '{workspace_name}' has no bounding box."

        personal_chat_button = page.locator(
            'button[aria-label="Navigates to a chat"]',
            has_text=re.compile(r"User .* (you)"),
        )

        await personal_chat_button.wait_for(state="visible", timeout=3000)

        personal_chat_box = await personal_chat_button.bounding_box()

        assert (
            personal_chat_box is not None
        ), f"Personal chat button with text 'User {email_alias} (you)' has no bounding box."

        assert (
            workspace_box != personal_chat_box
        ), "The bounding boxes of the workspace and personal chat buttons are the same."

        concierge_chat_button = page.locator(
            'button[aria-label="Navigates to a chat"]',
            has_text="Concierge",
        )

        await concierge_chat_button.wait_for(state="visible", timeout=3000)

        concierge_chat_box = await concierge_chat_button.bounding_box()

        assert (
            concierge_chat_box is not None
        ), "Concierge chat button has no bounding box."

        assert (
            workspace_box != concierge_chat_box
        ), "The bounding boxes of the workspace and concierge chat buttons are the same."

        # Close all tabs and browser
        await page.close()
        await context.close()
        await browser.close()
