import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import pytest
from playwright.async_api import async_playwright
from utils.trace_cleaner import trace_cleaner

email_address = "brighturing926+49933@gmail.com"
password = "sijknxflhloopmta"

@pytest.mark.asyncio
async def test_check_selfdm_isbold():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=[
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ])
        context = await browser.new_context()
        # Start recording the trace
        await context.tracing.start(screenshots=True, snapshots=True, sources=True)
        page = await context.new_page()

        try:
            await page.goto("https://dev.new.expensify.com:8082/")

            # Step 1: Log in user
            # Enter email
            await page.get_by_test_id("username").fill(email_address)
            await page.get_by_role("button", name="Continue").click()
            
            # Await OTP
            otp = "111111"
            await page.get_by_test_id("validateCode").fill(otp)
            
            # Step 2: Check if the self DM exists
            selfdm_span = page.locator('span', has_text="Dimaka Brown (you)")
            await selfdm_span.wait_for()

            # Step 3: Check the style of the self DM name
            tag_style = await selfdm_span.get_attribute("style")
            expected_tag_style = 'font-weight: 700;'
            assert expected_tag_style in tag_style, f"Expected self DM name to have '{expected_tag_style}', but got '{tag_style}'"
        except Exception as e:
            raise e
        finally:
            # Stop and save the trace
            await context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            # Clean the trace
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            # Ensure browser is closed
            await browser.close()
