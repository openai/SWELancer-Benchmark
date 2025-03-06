import os

import pytest
from playwright.async_api import Page, TimeoutError, async_playwright

EMAIL_USERNAME = "xecuycismfsga"
EMAIL_ALIAS = "8ita506t"
USER_EMAIL = f"{EMAIL_USERNAME}+{EMAIL_ALIAS}@gmail.com"
PASSWORD = "uwgb zzoc cofa kaaq"
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


async def close_button_if_present(page: Page):
    """
    Occasionally, there is a close button that prevents any clicks on the page as
    it covers most of the screen. This button cannot be seen visually.
    """
    close_button = page.locator('button[aria-label="Close"]')
    if await close_button.is_visible():
        await close_button.click()


@pytest.mark.asyncio
async def test_scroll_to_comments():
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
        page = await context.new_page()

        # admin login
        await login_or_create_user(page)
        await close_button_if_present(page)
        await page.get_by_role("button", name="Search").click()

        header = page.locator('div[data-drag-area="false"]').filter(has_text="Expenses")
        fifth_sibling = header.locator("xpath=following-sibling::*[5]")
        first_child_of_second_sibling = fifth_sibling.locator("xpath=descendant::*[1]")

        scroll_bar_width = await first_child_of_second_sibling.evaluate(
            'el => getComputedStyle(el).getPropertyValue("scrollbar-width")'
        )
        assert scroll_bar_width == "none", "There MUST not be a scrollbar"

        # Close all tabs and browser
        await page.close()
        await context.close()
        await browser.close()
