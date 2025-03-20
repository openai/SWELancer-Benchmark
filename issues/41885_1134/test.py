import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import pytest
from playwright.async_api import async_playwright

email_address = "brighturing926+49933@gmail.com"
password = ""

@pytest.mark.asyncio
async def test_check_selfdm_isbold():
    async with async_playwright() as p:


        browser = await p.chromium.launch(headless=True, args=[
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ])
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto("https://dev.new.expensify.com:8082/")



        await page.get_by_test_id("username").fill(email_address)
        await page.get_by_role("button", name="Continue").click()
  

        otp = "111111"
        await page.get_by_test_id("validateCode").fill(otp)
        

        selfdm_span = page.locator('span', has_text="Dimaka Brown (you)")
        await selfdm_span.wait_for()


        tag_style = await selfdm_span.get_attribute("style")
        expected_tag_style = 'font-weight: 700;'
        assert expected_tag_style in tag_style, f"Expected self DM name to have '{expected_tag_style}', but got '{tag_style}'"

        await browser.close()
