import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import base64
import io
import os
import pytest
from playwright.async_api import async_playwright, Page
from utils import login
from utils.trace_cleaner import trace_cleaner  # <--- Added import for trace_cleaner

PROXY_URL = os.getenv("PROXY_URL")
LOGIN_EMAIL = "testerfreelancer555+38130_rcrd@gmail.com"
EMAIL_PASSWORD = ""


IMAGE_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAIAAAACACAIAAABMXPacAAABLUlEQVR4nO3RQREAIAzAsIF/z0NGHjQKetczO4GuDvhdA7AGYA3AGoA1AGsA1gCsAVgDsAZgDcAagDUAawDWAKwBWAOwBmANwBqANQBrANYArAFYA7AGYA3AGoA1AGsA1gCsAVgDsAZgDcAagDUAawDWAKwBWAOwBmANwBqANQBrANYArAFYA7AGYA3AGoA1AGsA1gCsAVgDsAZgDcAagDUAawDWAKwBWAOwBmANwBqANQBrANYArAFYA7AGYA3AGoA1AGsA1gCsAVgDsAZgDcAagDUAawDWAKwBWAOwBmANwBqANQBrANYArAFYA7AGYA3AGoA1AGsA9gDO4gH/iDJCTQAAAABJRU5ErkJggg=="


async def reproduce_scenario(page: Page):

    await page.get_by_label("Workspaces").click()
    await page.get_by_label("New workspace").click()
    await page.get_by_label("Back").click()
    await page.get_by_test_id("selection-list").get_by_label(
        "'s Workspace"
    ).first.click()

    await page.get_by_label("Find something...").click()
    await page.get_by_test_id("selection-list-text-input").fill("Workspace")
    await page.get_by_test_id("selection-list").get_by_label(
        "'s Workspace"
    ).first.click()


    await page.get_by_role("button", name="Create").click()
    await page.get_by_label("Split expense").click()
    async with page.expect_file_chooser() as fc_info:
        await page.get_by_label("Choose file").click()
    file_chooser = await fc_info.value
    await file_chooser.set_files(
        [
            {
                "name": "image.png",
                "mimeType": "image/png",
                "buffer": io.BytesIO(base64.b64decode(IMAGE_BASE64)).getvalue(),
            }
        ]
    )

    await page.get_by_role("button", name="Split expense").click()


    try:
        await page.get_by_text("Receipt", exact=True).click()
    except:
        await page.get_by_text("Receipt", exact=True).nth(1).click()


    split_expense_button = page.get_by_role("button", name="Split expense")

    await split_expense_button.click()


    assert (
        not await split_expense_button.evaluate(
            "button => getComputedStyle(button).cursor"
        )
        == "not-allowed"
    ), "The 'Split expense' button is disabled based on cursor style; we don't disable buttons when there's an error on the form"


@pytest.mark.asyncio
async def test_split_expense():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=True,
            slow_mo=300,
            args=[
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
            ],
            proxy={"server": PROXY_URL} if PROXY_URL else None,
        )
        context = await browser.new_context(ignore_https_errors=True)
        page = await context.new_page()
        await login.sign_up(page, LOGIN_EMAIL)
        try:
            await login.complete_onboarding(page)
        except (AssertionError, TimeoutError):
            pass


        await context.tracing.start(
            title="test_split_expense",
            screenshots=True,
            snapshots=True
        )

        try:
            await reproduce_scenario(page)
        except Exception as e:
            raise e
        finally:
            trace_path = "/app/expensify/user_tool/output_browser1.zip"

            await context.tracing.stop(path=trace_path)

            trace_cleaner(trace_path)
