PROXY = True
PROXY_OTP = False

"""
The test verifies if the expected image is visible after clicking on the attachment from a markdown message through the search page.
"""

import pytest
from playwright.async_api import expect

from utils.login import sign_up, complete_onboarding
from utils.browser import start_browser, close_browser
from utils.email_handler import get_unique_derived_email

# Email
BASE_EMAIL = "testerfreelancer555@gmail.com"

@pytest.mark.asyncio
async def test_image_on_search_page():
    proxy = {"server":  "http://127.0.0.1:8080/"} if PROXY else None
    launch_args=[
    "--ignore-certificate-errors",
    "--disable-web-security",
    "--disable-features=IsolateOrigins,site-per-process"
    ]
    context, page, playwright = await start_browser(launch_args=launch_args, slow_mo=500, proxy=proxy)
    try:
        # Log in the user
        # email = get_unique_derived_email(email=BASE_EMAIL)
        email = "testerfreelancer555+1739550397@gmail.com"
        await sign_up(page, email=email)
        await complete_onboarding(page, "Test", "User")
        await page.get_by_text("Test User (you)").click()
        await page.locator("#composer").fill("*test* ![demo image](https://camo.githubusercontent.com/4848d0f965f332077b77a1a0488c3e66b4769032104f4de6890bae218b4add8d/68747470733a2f2f70696373756d2e70686f746f732f69642f313036372f3230302f333030) _test_")
        await page.get_by_label("Send").click()
        await page.get_by_test_id("CustomBottomTabNavigator").get_by_label("Search").click()
        await page.get_by_text("Chats").click()
        await page.get_by_test_id("selection-list").get_by_label("View attachment").click()
        await expect(page.get_by_label("68747470733a2f2f70696373756d2e70686f746f732f69642f313036372f3230302f333030.jpg").locator("img")).to_be_visible()

    finally:
        await close_browser(context, page, playwright)
