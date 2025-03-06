import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import secrets
import string
import time
from email.header import decode_header

import pyotp
import pyperclip
import pytest
from playwright.async_api import Page, TimeoutError, async_playwright, expect

USER_EMAIL = "expensifysam@gmail.com"
PASSWORD = ""
SLOW_MO: float | None = 500
NOW = int(time.time())


def generate_random_string(length=12):

    random_bytes = secrets.token_bytes(length)
    base64_string = secrets.base64.b64encode(random_bytes).decode("utf-8")


    alphanumeric_string = "".join(
        filter(lambda x: x in string.ascii_letters + string.digits, base64_string)
    )


    return alphanumeric_string[:length]


async def create_user(page: Page, firstname: str, lastname: str):
    await page.get_by_role("button", name="Join").click()


    await page.get_by_text("Track and budget expenses").click()
    await page.get_by_role("textbox", name="First name").fill(firstname)
    await page.get_by_role("textbox", name="Last name").fill(lastname)
    await page.get_by_role("button", name="Continue").click()


async def login(page: Page, user_email: str, password: str):

    magic_code = "123456"
    await page.get_by_role("textbox").fill(magic_code)


async def login_or_create_user(page: Page, user_email: str, password: str):
    await page.get_by_test_id("username").fill(user_email)
    await page.get_by_role("button", name="Continue").click()

    try:
        await page.get_by_role("button", name="Join").wait_for(
            state="visible", timeout=2000
        )
        firstname, lastname = generate_random_string(6), generate_random_string(6)
        await create_user(page, firstname, lastname)
    except TimeoutError:
        await login(page, user_email, password)


async def verify_email(page: Page):
    await page.get_by_label("My settings").click()
    await page.get_by_role("menuitem", name="Profile").click()
    await page.get_by_text("Contact method").click()
    await page.get_by_test_id("ContactMethodsPage").get_by_text(USER_EMAIL).click()

    if await page.get_by_text("Please enter the magic code sent to").is_visible():
        magic_code = "123456"
        await page.get_by_role("textbox").fill(magic_code)
        await page.get_by_role("button", name="Verify").click()
        await page.get_by_text("Add more ways for people to").wait_for(state="visible")
        await page.get_by_label("Back").first.click()  # Go back to settings page
    else:
        await page.get_by_test_id("ContactMethodDetailsPage").get_by_label(
            "Back"
        ).click()
        await page.get_by_label("Back").first.click()  # Go back to settings page


async def enable_two_factor_authentication(page: Page):

    await page.get_by_label("Security").click()
    await page.get_by_label("Two-factor authentication").click()
    await page.get_by_text("Copy").click()  # copy recovery codes

    with open("recovery_codes.txt", "w", encoding="utf-8") as f:
        f.write(pyperclip.paste())
    await page.get_by_role("button", name="Next").click()


    await page.get_by_text("Or add this secret key to").wait_for(
        state="visible", timeout=2000
    )
    await page.get_by_text("Copy").click()
    secret_key = pyperclip.paste()


    totp = pyotp.TOTP(secret_key)
    otp = totp.now()
    await page.get_by_role("textbox").fill(otp)

    await page.get_by_text("Two-factor authentication is").wait_for(
        state="visible", timeout=2000
    )

    await page.get_by_role("button", name="Got it").click()
    await page.get_by_label("Back").click()  # Go back to settings page


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


async def sign_in_with_incorrect_otp(page: Page):
    now = int(time.time()) - 1000  # 1 second ago

    await page.get_by_test_id("username").fill(USER_EMAIL)
    await page.get_by_role("button", name="Continue").click()

    magic_code = "654321"
    await page.get_by_role("textbox").fill(magic_code)

    await enter_incorrect_otp(page)


@pytest.mark.asyncio
async def test_recovery_code_login():

    async with async_playwright() as p:

        browser = await p.chromium.launch(headless=True, slow_mo=SLOW_MO, args=[
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ])
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto("https://dev.new.expensify.com:8082/")


        await login_or_create_user(page, USER_EMAIL, PASSWORD)

        try:
            await page.get_by_text("Please enter your authenticator code").wait_for(
                state="visible", timeout=2000
            )


            await enter_incorrect_otp(page)
            return
        except TimeoutError:
            pass


        await verify_email(page)


        await enable_two_factor_authentication(page)


        await page.get_by_label("Sign out").click()


        await sign_in_with_incorrect_otp(page)


        await context.close()
        await browser.close()

