import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

PROXY = False
PROXY_OTP = True

from utils.trace_cleaner import trace_cleaner

"""
The test verifies if the clear button appears and works correctly when renaming a saved search filter.
"""

import pytest
from playwright.async_api import Page, expect, async_playwright

from utils.login import sign_in
from utils.email_handler import EmailHandler
from utils.browser import start_browser, close_browser
from utils.email_handler import get_specific_derived_email

# Email
BASE_EMAIL = "testerfreelancer555@gmail.com"
PASSWORD = "snct ajbr yadx kwlq"
ISSUE_NUMBER = "50163"

async def sign_in_new_dot(page: Page, email: str, password: str):
    """
    Sign in into the new Expensify dot.
    """
    
    # Sign In
    with EmailHandler(email, password) as email_handler:
        if not PROXY_OTP: 
            email_handler.clean_inbox()  # Clean inbox

        await page.goto("https://dev.new.expensify.com:8082")
        # Enter email
        await page.get_by_test_id("username").fill(email)
        await page.get_by_role("button", name="Continue").click()
  
        # Await OTP
        otp = "123456" if PROXY_OTP else email_handler.read_otp_code()
        await page.wait_for_timeout(1000) if PROXY_OTP else False
        await page.get_by_test_id("validateCode").fill(otp)

        # Wait sign in to complete
        await page.get_by_text("Please enter the magic code").wait_for(state="hidden")

@pytest.mark.asyncio
async def test_search_expensify():
    async with async_playwright() as playwright:
        proxy = {"server":  "http://127.0.0.1:8080/"} if PROXY else None
        launch_args=[
            "--ignore-certificate-errors",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ]
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(slow_mo=2000, headless=True, args=launch_args, proxy=proxy)
        context = await browser.new_context()
        trace_path = "/app/expensify/user_tool/output_browser1.zip"

        # Start tracing
        await context.tracing.start(screenshots=True, snapshots=True)

        page = await context.new_page()
        try:
            # Log in the users
            email_admin = get_specific_derived_email(email=BASE_EMAIL, suffix=ISSUE_NUMBER)
            await sign_in_new_dot(page, email=email_admin, password=PASSWORD)

            # Open Search page
            await page.locator("button[aria-label='Search']").click()
            # Make a random search
            await page.locator("div[aria-label='Search'][id='searchButton']").locator("visible=true").click()
            await page.wait_for_timeout(1000)
            await page.locator("input[aria-label='Search for something']").fill("test")
            await page.locator("button[aria-label='test']").locator("visible=true").click()
            # Save the current search
            await page.locator("button:has-text('Filters')").locator("visible=true").click()
            await page.locator("button:has-text('Save')").locator("visible=true").click()
            await page.wait_for_timeout(1000)

            # Start to rename the saved search and clean the name
            await page.locator("button[aria-label='More']").locator("visible=true").click()
            await page.locator("div[role='menuitem'][aria-label='Rename']").locator("visible=true").click()
            await page.locator("input[aria-label='Search name']").locator("visible=true").click()
            # Attempt to verify the presence of the Clear button ('x' icon) and click it
            clear_button = page.locator("button[aria-label='Clear']")
            await clear_button.wait_for(timeout=3000)  # Adjust timeout as needed
            await clear_button.click()
            await expect(page.get_by_role("textbox", name="Search name")).to_be_empty()

        finally:
            # Stop tracing and clean the trace
            await context.tracing.stop(path=trace_path)
            trace_cleaner(trace_path)
            await close_browser(context, page, playwright)
