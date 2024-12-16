import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import pytest
from playwright.async_api import Page, TimeoutError, async_playwright, expect

USER_EMAIL = "xecuycismfsga+28092_21@gmail.com"
PASSWORD = "uwgb zzoc cofa kaaq"



async def create_user(page: Page, firstname: str, lastname: str):
    await page.get_by_role("button", name="Join").click()

    # Update profile
    await page.get_by_text("Track and budget expenses").click()
    await page.get_by_role("textbox", name="First name").fill(firstname)
    await page.get_by_role("textbox", name="Last name").fill(lastname)
    await page.get_by_role("button", name="Continue").click()


async def login(page: Page, user_email: str, password: str):
    # get current timestamp

    await page.get_by_role("textbox").fill("896968")


async def login_or_create_user(page: Page, user_email: str, password: str):
    await page.get_by_test_id("username").fill(user_email)
    await page.get_by_role("button", name="Continue").click()

    try:
        await page.get_by_role("button", name="Join").wait_for(
            state="visible"
        )
        firstname, lastname = "yagna", "sai"
        await create_user(page, firstname, lastname)
    except TimeoutError:
        await login(page, user_email, password)


async def verify_email(page: Page):
    await page.get_by_label("My settings").click()
    await page.get_by_role("menuitem", name="Profile").click()
    await page.get_by_text("Contact method").click()
    await page.get_by_test_id("ContactMethodsPage").get_by_text(USER_EMAIL).click()

    if await page.get_by_text("Please enter the magic code sent to").is_visible():

        await page.get_by_role("textbox").fill("896968")
        await page.get_by_role("button", name="Verify").click()
        await page.get_by_text("Add more ways for people to").wait_for(state="visible")
        await page.get_by_label("Back").first.click()  # Go back to settings page
    else:
        await (
            page.get_by_test_id("ContactMethodDetailsPage").get_by_label("Back").click()
        )
        await page.get_by_label("Back").first.click()  # Go back to settings page




async def enter_incorrect_otp(page: Page):
    await page.get_by_text("Please enter your authenticator code").wait_for(
        state="visible", timeout=2000
    )
    await page.get_by_role("textbox").fill("123456")  # enter incorrect otp
    await expect(
        page.get_by_text("Please enter a valid authenticator code")
    ).to_be_visible()

    await page.get_by_label("Use recovery code").click()
    await page.get_by_role("textbox", name="Recovery code").fill("werwer")
    await page.get_by_role("textbox", name="Recovery code").press("Enter")
    await expect(page.get_by_text("Incorrect recovery code.")).to_be_visible()



@pytest.mark.asyncio
async def test_recovery_code_login():
    async with async_playwright() as p:
        # Launch chromium and open new page
        browser = await p.chromium.launch(channel="chrome", headless=True, slow_mo=2100, args=[
            "--ignore-certificate-errors",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ])
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto("https://dev.new.expensify.com:8082/")

        # Login or create user
        await login_or_create_user(page, USER_EMAIL, PASSWORD)

        try:
            await page.get_by_text("Please enter your authenticator code").wait_for(
                state="visible"
            )

            # Sign in with incorrect OTP
            await enter_incorrect_otp(page)
            return
        except TimeoutError:
            pass


        # Verify email
        await verify_email(page)

        # ---------------------
        await context.close()
        await browser.close()
