import re
import random
import imaplib
import logging
import email
from playwright.sync_api import Page, expect, sync_playwright
from utils.trace_cleaner import trace_cleaner

EMAIL = "velmoner+960@gmail.com"
PASSWORD = "aory ezrb qkmi qkas"
NEWDOT_URL = "https://dev.new.expensify.com:8082/"
first_name = "aa"
last_name = "bb"


def user_login(page: str, email_id: str):
    page.goto(NEWDOT_URL)

    page.locator('input[type="email"]').fill(email_id)
    page.wait_for_timeout(2000)
    page.get_by_role("button", name="Continue").nth(0).click()
    page.wait_for_timeout(10000)
    otp = "123456"
    page.locator('input[data-testid="validateCode"]').fill(otp)
    try:
        page.get_by_role("button", name="Sign In").click()
    except Exception as err:
        pass


def test_expensify_17387():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            proxy={"server": "http://localhost:8080"},
            headless=False,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"],
            slow_mo=None,
            channel="chromium"
        )
        context = browser.new_context()

        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        page = context.new_page()

        try:
            invalid_email = """jaj@asjjssjdjdjdjdjdjjeiwiwiwowkdjdjdieikdjfidekjcjdkekejdcjdkeekcjcdidjjcdkekdiccjdkejdjcjxisdjjdkedncicdjejejcckdsijcjdsodjcicdkejdicdjejajasjjssjdjdjdjdjdjjeiwiwiwo\nwkdjdjdieikdjfisjksksjsjssskssjskskssksksksksskdkddkddkdksskskdkdkdksskskskdkdkdkdkekeekdkddenejeodxkdndekkdjddkeemdjxkdenendkdjddekjcjdkekejdcjdkeekcjcdidjjcdkekdiccjdkejdjcjxisdjjdkedncicdjejejcckdsijcjdsodjcicdkejdi.cdjd"""

            page.goto(NEWDOT_URL)


            page.get_by_test_id("username").fill(invalid_email)
            page.get_by_role("button", name="Continue").click()
            assert page.get_by_text("The email entered is invalid.").is_visible()

            user_login(page=page, email_id=EMAIL)
            page.wait_for_timeout(2000)


            page.get_by_label("Start chat (Floating action)").click()
            page.get_by_role("menuitem", name="Start chat").click()
            page.wait_for_timeout(500)
            page.get_by_role("textbox", name="Name, email, or phone number").fill(invalid_email)
            page.wait_for_timeout(500) # intentional delay to allow validation to complete
            assert page.get_by_text("Invalid email").is_visible()


            page.get_by_label("back").click()
            page.get_by_label("Settings").click()
            page.get_by_role("menuitem", name="Profile").click()
            page.get_by_text("Contact method").click()
            page.get_by_role("button", name="New contact method").click()
            page.get_by_role("textbox", name="Email/Phone number").fill(invalid_email)
            page.get_by_role("button", name="Add").click()
            assert page.get_by_text("Invalid contact method").is_visible()
        except Exception as e:

            print(f"An error occurred: {e}")
        finally:

            context.tracing.stop()
            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            context.tracing.export(path=trace_path)

            trace_cleaner(trace_path)

            context.close()
            browser.close()
