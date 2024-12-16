import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

"""
The test verifies if the offline indicator is correctly shown at the bottom of the screen.
"""
import pytest
from playwright.async_api import expect, async_playwright, Browser, Page
from utils.login import sign_up, NEW_DOT_URL, complete_onboarding
from utils.browser import close_browser
from utils.email_handler import get_specific_derived_email

# Email
BASE_EMAIL = "totherandomuser@gmail.com"
PASSWORD = "umeidjwibfmpjntm"


# Set up browser
async def start_browser_with_proxy(mobile_device: str):
    playwright = await async_playwright().start()
    device_profile = playwright.devices[mobile_device] if mobile_device else {}
    browser = await playwright.chromium.launch(
        slow_mo=600,
        headless=True,
        proxy={
            'server': 'http://127.0.0.1:8080'
        },
        args=[
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process'
        ]
    )
    context = await browser.new_context(ignore_https_errors=True, **device_profile)
    page = await context.new_page()
    return context, page, playwright


@pytest.mark.asyncio
async def test_offline_indicator():
    try:
        context, page, playwright = await start_browser_with_proxy(mobile_device='iPhone 12 Pro')

        # Step 1: Login / Sign up with a new account
        derived_email = get_specific_derived_email(email=BASE_EMAIL, suffix='128937')
        await sign_up(page, derived_email)

        # Complete onboarding if modal is visible
        try:
            await complete_onboarding(page, first_name='Deepak', last_name='Dhaka')
        except Exception:
            pass

        # Following block of code is for an unexpected concierge get started and concierge chat pop-up
        await page.wait_for_timeout(2000)
        if await page.locator('button:has-text("Get started")').is_visible():
            await page.locator('button:has-text("Get started")').click()
            if await page.get_by_label('Back').is_visible():
                await page.get_by_label('Back').click()

        # Make sure inbox is visible and continue with the test
        await expect(page.get_by_label("Inbox")).to_be_visible()

        # Step 2:
        await page.get_by_label("My settings").click()
        await page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").get_by_text("Workspaces").click()
        await page.locator('button:has-text("New workspace")').first.click()
        await page.get_by_text("More features").click()

        # Locate the toggle button by aria-label
        toggle_button = page.get_by_role("switch", name="Gain insights and control over spend")

        # Check if the button is already in the "on" state by inspecting aria-checked
        is_on = await toggle_button.get_attribute("aria-checked") == "true"
        if not is_on:
            await toggle_button.click()
            print("Button was off, now turned on.")
        else:
            print("Button is already on; clickiing twice!!")
            await toggle_button.click()
            await toggle_button.click()

        # Step 3: The loader takes time to load, so sleep is must.
        await page.wait_for_timeout(1000)

        await page.get_by_test_id("WorkspaceInitialPage").get_by_text("Expensify Card").click()
        await page.get_by_role("button", name="Issue card").click()
        await page.get_by_test_id("selection-list").get_by_label("Deepak Dhaka").click()

        # set offline and check for the text position
        text_to_find = "You appear to be offline."
        elements = page.locator(f"text={text_to_find}")
        await context.set_offline(True)

        # Iterate through each element and print its position
        y_pos = []
        count = await elements.count()
        if count > 0:
            for i in range(count):
                bounding_box = await elements.nth(i).bounding_box()
                if bounding_box:
                    print(f"Element {i+1} position: {bounding_box}")

                    y_pos.append(bounding_box['y'])

        assert 361 not in y_pos, "You appear to be offline, has been found at an unusual location."

    finally:
        await close_browser(context, page, playwright)