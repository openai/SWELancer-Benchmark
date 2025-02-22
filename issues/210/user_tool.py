import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from typing import Any
from playwright.sync_api import sync_playwright
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page
import logging

from utils.trace_cleaner import trace_cleaner

logging.basicConfig(level=logging.INFO)

master_email_address = "brighturing926+50155@gmail.com"
master_app_password = "sijknxflhloopmta"
dev_base_url = "https://dev.new.expensify.com:8082"


def login_user(p: PlaywrightContextManager, user_email: str) -> tuple[Browser, Page, Any]:

    browser = p.chromium.launch(headless=True, slow_mo=1000, args=["--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"])
    context = browser.new_context()
    page: Page = context.new_page()


    page.goto(dev_base_url)


    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()

    my_otp_code = "123456"
    page.get_by_test_id("validateCode").fill(my_otp_code)


    try:
        page.get_by_role("button", name="Sign in").click()
    except Exception:
        pass

    return browser, page, context


def test_country_select_display_profile() -> None:
    with sync_playwright() as p:

        browser, page, context = login_user(p, master_email_address)


        context.tracing.start(screenshots=True, snapshots=True, sources=True)

        try:

            page.get_by_label("Start chat (Floating action)").click()
            page.get_by_label("Book travel").click()
            page.get_by_label("Book travel").click()
            page.get_by_role("menuitem", name="Country").click()


            page.locator("#overLayBottomButton").click()
            profile_text = "These details are displayed on your public profile. Anyone can see them."
            profile_page = page.get_by_text(profile_text, exact=True)

            assert not profile_page.is_visible(), "Profile page is shown when country is selected"
        except Exception as e:
            logging.exception("Test failed.")
            raise e
        finally:

            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")


            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")


            browser.close()
