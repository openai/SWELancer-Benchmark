import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

"""
This test script was written to test the issue #42284.

Pre-conditions:
- Workspace is created.
- Distance rate configuration is enabled.
- Only default rate present.

Test Steps:
- Set a new distance rate.
- Disable the default rate.
- Submit a distance expense and check if the default rate is the new rate.
"""


import pytest
from playwright.async_api import async_playwright, Page
from utils.email_handler import EmailHandler, get_specific_derived_email
from utils.browser import close_browser, start_browser


BASE_EMAIL = "lucassandboxturing@gmail.com"
PASSWORD = "vvdc gwak mcee hkjj"
PROXY_OTP = True  # Set to True if you are replaying the recorded test flow
WS_NAME = f"Lucassandboxturing+42284's"


async def start_browser(headless=True, slow_mo=100, launch_args=None):
    """
    Start a browser instance with the given parameters.

    :param headless: Boolean to specify if the browser should run in headless mode.
    :param slow_mo: Slow down the browser operations by the specified amount of milliseconds.
    :param launch_args: List of arguments to pass to the browser instance.
    :return: A tuple of (context, page, playwright).
    """
    
    if launch_args is None:
        launch_args = ["--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"]


    playwright = await async_playwright().start()
    context, page = None, None
    

    browser = await playwright.chromium.launch(headless=headless, args=launch_args, slow_mo=slow_mo)
    context = await browser.new_context(ignore_https_errors=True)
    page = await context.new_page()

    return context, page, playwright


async def sign_in_new_dot(page: Page, email: str, password: str):
    """
    Sign in into the new Expensify dot.
    """
    

    url = "https://dev.new.expensify.com:8082"
    await page.goto(url)
    

    with EmailHandler(email, password) as email_handler:
        if not PROXY_OTP:
            email_handler.clean_inbox()  # Clean inbox


        await page.get_by_test_id("username").fill(email)
        await page.get_by_role("button", name="Continue").click()
  

        otp = "123456" if PROXY_OTP else email_handler.read_otp_code()
        await page.get_by_test_id("validateCode").fill(otp)


        await page.get_by_text("Please enter the magic code").wait_for(state="hidden")


async def set_distance_rate(page: Page) -> None:
    

    await page.get_by_label("My settings").click()
    await page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").get_by_text("Workspaces").click()
    await page.locator(f"text={WS_NAME} Workspace").last.click()
    await page.get_by_text("Distance rates").click()
    

    await page.get_by_role("button", name="Add rate").click()
    await page.get_by_placeholder("0").fill("0.5")
    await page.get_by_role("button", name="Save").click()
    

    await page.locator("[id=\"\\32 17EA6359859B\"]").get_by_label("R$0.6700 / mile").click()
    await page.get_by_role("button", name="selected").click()
    await page.get_by_text("Disable rate").click()
    

    await page.get_by_label("Back").click()
    await page.get_by_label("Inbox").click()
    await page.locator("text=Bob Bill (you)").click()


async def set_submit_expense(page: Page) -> None:
    

    await page.get_by_label("Start chat (Floating action)").click()
    await page.get_by_text("Submit expense", exact=True).click()
    

    await page.get_by_label("Distance").click()
    

    await page.get_by_test_id("IOURequestStartPage").get_by_role("button", name="Start").click()
    await page.get_by_test_id("IOURequestStepWaypoint").get_by_role("textbox").fill("NYC")
    await page.get_by_text("NYC", exact=True).click()
    await page.get_by_role("button", name="Stop").click()
    await page.get_by_test_id("IOURequestStepWaypoint").get_by_role("textbox").fill("Liberty")
    await page.get_by_text("Liberty State Park").click()
    

    await page.locator("text=Next").last.click()
    

    await page.get_by_label(WS_NAME).click()
    

async def reproduce_scenario(page: Page) -> None:
    

    await set_distance_rate(page)
    

    await set_submit_expense(page)


    assert await page.get_by_text("mi @ R$0.50 / mi").is_visible()

@pytest.mark.asyncio
async def test_disabled_rate_test() -> None:
    
    try:

        context, page, playwright = await start_browser(slow_mo=500)
        

        user_email = get_specific_derived_email(BASE_EMAIL, 42284)
        await sign_in_new_dot(page, user_email, PASSWORD)


        await page.wait_for_timeout(2000)
        await reproduce_scenario(page)

    finally:

        await close_browser(context, page, playwright)
