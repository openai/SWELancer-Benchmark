import platform

import pytest
from playwright.async_api import async_playwright

from utils.login import sign_in_new_dot

EMAIL = "adnan.expensified+adslfkj8024adjsf@gmail.com"
PASSWORD = "mcak rifc vlgg brko"


@pytest.mark.asyncio
async def test_51894():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            proxy={"server": "http://127.0.0.1:8080/"},
            args=[
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
            ],
        )
        context = await browser.new_context(ignore_https_errors=True)
        page = await context.new_page()

        await page.goto("https://dev.new.expensify.com:8082/")
        await sign_in_new_dot(page, EMAIL, PASSWORD, True)
        # Detect OS and press the appropriate key combination
        await page.wait_for_timeout(2000)

        if platform.system() == "Darwin":  # macOS
            await page.keyboard.press("Meta+k")  # CMD+K
        else:
            await page.keyboard.press("Control+k")  #

        first_result = page.locator('[data-testid="selection-list"] button').nth(1)
        second_result = page.locator('[data-testid="selection-list"] button').nth(2)

        # Get background color of both elements
        first_bg_color = await first_result.evaluate(
            "el => window.getComputedStyle(el).backgroundColor"
        )
        second_bg_color = await second_result.evaluate(
            "el => window.getComputedStyle(el).backgroundColor"
        )

        # Assert the first item is highlighted (background color should NOT be the same as the second)

        assert (
            first_bg_color != second_bg_color
        ), "Test failed! First search result is not highlighted!"

        await page.close()
        await context.close()
        await browser.close()
