import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import pytest
from playwright.async_api import Page, async_playwright, expect
from utils.trace_cleaner import trace_cleaner

USER_NAME = "xecuycismfsga+42204"
USER_EMAIL = f"{USER_NAME}@gmail.com"
PASSWORD = "uwgb zzoc cofa kaaq"


def get_magic_code(
    user_email: str, password: str, current_timestamp: int, retries=5, delay=3
):
    return "123456"


async def login(page: Page, user_email: str, password: str):

    now = 20241211
    await page.get_by_test_id("username").fill(user_email)
    await page.get_by_role("button", name="Continue").click()
    await page.wait_for_timeout(3000)  # keeps getting old otp
    magic_code = get_magic_code(user_email, password, now, retries=3, delay=3)
    await page.get_by_role("textbox").fill(magic_code)
    await page.get_by_label("Inbox").wait_for(state="visible")


async def close_button_if_present(page: Page):
    """
    Occasionally, there is a close button that prevents any clicks on the page as
    it covers most of the screen. This button cannot be seen visually.
    """
    close_button = page.locator('button[aria-label="Close"]')
    if await close_button.is_visible():
        await close_button.click()


async def leave_group_chat(page: Page):
    if await page.get_by_text(USER_NAME).first.is_visible():

        await page.get_by_text(USER_NAME).first.click()
        await page.locator(
            f'div[data-testid="DisplayNamesWithTooltip"]:has-text("{USER_NAME}")'
        ).last.click()
        await page.get_by_label("Leave").click()
        await page.get_by_label("Back").first.click()


@pytest.mark.asyncio  # ensure you have pytest-asyncio installed
async def test_leave_group_chat():

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, slow_mo=500, args=[
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
        ])

        context = await browser.new_context()

        await context.tracing.start(screenshots=True, snapshots=True, sources=True)
        page = await context.new_page()

        try:

            await page.goto("https://dev.new.expensify.com:8082/")
            await login(page, USER_EMAIL, PASSWORD)


            await leave_group_chat(page)


            await close_button_if_present(page)
            await page.get_by_label("Start chat (Floating action)").click()
            await page.get_by_label("Start chat", exact=True).click()
            await page.get_by_test_id("selection-list-text-input").fill(
                f"{USER_NAME}_0@gmail.com"
            )
            await page.get_by_role("button", name="Add to group").click()
            await page.get_by_role("button", name="Next").click()
            await page.get_by_role("button", name="Start group").click()


            await page.get_by_role("textbox").fill("Hello World")
            await page.get_by_role("button", name="Send").click()


            await page.locator(
                f'div[data-testid="DisplayNamesWithTooltip"]:has-text("{USER_NAME}_0@gmail.com")'
            ).last.click()


            await page.get_by_label("Members").click()
            await page.get_by_label(f"{USER_NAME}_0@gmail.com").last.click()
            await page.get_by_role("button", name="selected").click()
            await page.get_by_label("Remove members").click()
            await page.get_by_role("button", name="Remove").click()


            await page.get_by_test_id("ReportParticipantsPage").get_by_label("Back").click()
            await page.get_by_label("Leave").click()

            await expect(page.get_by_role("button", name="Leave")).to_be_visible()
            await page.get_by_role("button", name="Leave").click()

        finally:

            await context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")


        await context.close()
        await browser.close()
