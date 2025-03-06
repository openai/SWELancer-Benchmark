import os
import pytest
from playwright.async_api import Browser, Page, TimeoutError, async_playwright
from utils.trace_cleaner import trace_cleaner

EMAIL_USERNAME = "xecuycismfsga"
EMAIL_ALIAS = "r5p4hfur"
USER_EMAIL = f"{EMAIL_USERNAME}+{EMAIL_ALIAS}@gmail.com"
PASSWORD = ""
SLOW_MO: int | None = 500
PROXY_URL = os.getenv("PROXY_URL")

LONG_FIRSTNAME = "XzH9tXRklkFrTjMU"
LONG_LASTNAME = "MwuCGEtROJc5CZz9"
PARTICIPANT_ALIAS = "wzec6tou"
PARTICIPANT_EMAIL = f"{EMAIL_USERNAME}+{PARTICIPANT_ALIAS}@gmail.com"


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


async def create_participant_account(browser: Browser):
    context_1 = await browser.new_context()
    await context_1.tracing.start(screenshots=True, snapshots=True, sources=True)
    page_1 = await context_1.new_page()
    try:
        await login_or_create_user(
            page_1,
            user_email=PARTICIPANT_EMAIL,
            firstname=LONG_FIRSTNAME,
            lastname=LONG_LASTNAME,
        )
    finally:
        await context_1.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
        trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
        await page_1.close()
        await context_1.close()


async def submit_expense(page: Page):
    await page.get_by_label("Create").last.click()
    await page.get_by_label("Submit expense").click()
    await page.get_by_label("Manual").click()
    await page.get_by_placeholder("0").fill("1000000")
    await (
        page.locator("#numPadContainerView").get_by_role("button", name="Next").click()
    )
    await page.get_by_role("button", name="Submit").click()


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
        try:
            await create_participant_account(browser)

            iphone = p.devices["iPhone SE"]
            context = await browser.new_context(**iphone)
            await context.tracing.start(screenshots=True, snapshots=True, sources=True)
            page = await context.new_page()

            try:
                await login_or_create_user(page)

                participant_chat = page.locator(
                    'button[aria-label="Navigates to a chat"]',
                    has_text=f"{LONG_FIRSTNAME} {LONG_LASTNAME}",
                ).first

                try:
                    await participant_chat.click(timeout=3000)
                except TimeoutError:
                    await page.get_by_label("Start chat (Floating action)").click()
                    await page.get_by_label("Start chat", exact=True).click()
                    await page.get_by_test_id("selection-list-text-input").fill(
                        PARTICIPANT_EMAIL
                    )
                    await page.get_by_label(PARTICIPANT_EMAIL).click()

                expense_preview = (
                    page.get_by_role("button", name="View details")
                    .filter(has_text=f"{LONG_FIRSTNAME} owes:")
                    .last
                )

                try:
                    await expense_preview.click(timeout=3000)
                except TimeoutError:
                    await submit_expense(page)

                right_margin = await page.locator(
                    "div[id='searchButton'][aria-label='Search']"
                ).last.evaluate("el => getComputedStyle(el).marginRight")

                assert right_margin != "0px", "Right margin should not be zero pixels"
            finally:
                await context.tracing.stop(path="/app/expensify/user_tool/output_browser2.zip")
                trace_cleaner("/app/expensify/user_tool/output_browser2.zip")
                await page.close()
                await context.close()
        finally:
            await browser.close()