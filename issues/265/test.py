import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import pytest
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page

EMAIL = "t1533148@gmail.com" # for example test+1234@gmail.com
PASSWORD = "logb hzkg pkfk kskg" # it will be something like "sdib pxop ovyl uawy"



def signup_user(page, user_email, first_name, last_name) -> tuple[Page, str, str, str]:
    page.goto('https://127.0.0.1:8082/')
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(2000)
    
    otp = '123456'
    page.locator('input[name="validateCode"]').fill(otp)
    page.wait_for_timeout(2000)

        

def run_test(page: Page) -> None:
    page.get_by_label("Start chat (Floating action)").click()
    page.wait_for_timeout(1000)
    page.get_by_text("Start chat").click()
    page.wait_for_timeout(1000)
    page.get_by_test_id("selection-list-text-input").fill("a@a.com")
    page.wait_for_timeout(1000)
    page.get_by_role("button", name="Add to group").click()
    page.wait_for_timeout(1000)
    page.get_by_role("button", name="Next").click()
    page.wait_for_timeout(1000)
    page.get_by_role("button", name="Start group").click()
    page.wait_for_timeout(1000)
    page.get_by_role("textbox").fill("Hello message 1")
    page.wait_for_timeout(3000)
    page.get_by_label("Send").click()
    page.wait_for_timeout(3000)
    page.get_by_role("textbox").fill("Hello message 2")
    page.wait_for_timeout(1000)
    page.get_by_label("Send").click()
    page.wait_for_timeout(2000)


    page.locator('button[aria-label*="Ak, Hidden"][role="button"]').nth(-1).click()
    page.wait_for_timeout(3000)
    page.get_by_label("Members").click()
    page.wait_for_timeout(1000)
    page.get_by_label("Hidden").nth(-1).click()
    page.wait_for_timeout(1000)
    page.get_by_role("button", name="Remove from group").click()
    page.wait_for_timeout(1000)
    page.get_by_role("button", name="Remove", exact=True).click()
    page.wait_for_timeout(1000)


    page.get_by_test_id("ReportParticipantsPage").get_by_label("Back").click()
    page.wait_for_timeout(1000)
    page.get_by_label("Leave").click()
    page.wait_for_timeout(1000)
    page.get_by_role("button", name="Leave").click()
    page.wait_for_timeout(1000)
    page.get_by_role("button", name="Back", exact=True).click()

    page.wait_for_timeout(3000)

    is_main_page_visible = bool(page.get_by_label("Workspaces").is_visible())


    is_error_visible = page.locator("text=Hmm... it's not hereYou don't").is_visible()
    if (is_error_visible):
        raise AssertionError("Error message was visible, test failed.")
    elif (is_main_page_visible!=True):
        raise AssertionError("Screen is loading for too long.")
    else:
        print("Test passed: Error message was not visible.")


@pytest.mark.parametrize("first_name, last_name", [("AK", "Test")])
def test_expensify(first_name: str, last_name: str) -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='chrome', headless=True, slow_mo=1000,
            proxy = {"server": "http://127.0.0.1:8080/"},
            args=[
            "--ignore-certificate-errors",
            "--disable-web-security", 
            "--disable-features=IsolateOrigins,site-per-process"
        ])
        context_args = {}
        context_args["geolocation"] = {"latitude": 37.7749, "longitude": 122.4194}
        context_args["permissions"] = ["geolocation"]
        context_args["viewport"] = {"width": 375, "height": 550}
        context_args["ignore_https_errors"] = True

        context = browser.new_context(**context_args)
        page = context.new_page()
        signup_user(page, EMAIL, first_name, last_name)
        run_test(page)

        browser.close()