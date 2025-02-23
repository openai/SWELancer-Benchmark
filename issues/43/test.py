import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError



def generate_random_email():
    timestamp = int(time.time())

    return "t56826807+1733396881@gmail.com"


def login_user(
    p: PlaywrightContextManager, first_name="A", last_name="Khan"
) -> tuple[Browser, Page, str]:

    browser = p.chromium.launch(
        channel="chrome",
        headless=True,
        args=[
            "--ignore-certificate-errors",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
        ],
        proxy={"server": "http://localhost:8080"},
        slow_mo=500,
    )
    context = browser.new_context()
    page = context.new_page()
    user_email = generate_random_email()


    page.goto("https://dev.new.expensify.com:8082/")


    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()
    time.sleep(1)


    try:
        page.locator('button[tabindex="0"]').click()
        time.sleep(1)
    except Exception:
        pass


    expect(page.locator("text=What do you want to do today?")).to_be_visible()


    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()
    time.sleep(1)


    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()
    time.sleep(1)


    return browser, page, context


def test_old_dot_page_redirection():
    with sync_playwright() as p:
        browser, page, context = login_user(p)


        page.goto("https://dev.new.expensify.com:8082/settings/exit-survey/reason")
        time.sleep(1)


        expect(page).to_have_url(
            "https://dev.new.expensify.com:8082/settings/exit-survey/reason"
        )


        page.get_by_text("I don't understand how to use New Expensify.").click()


        expect(
            page.get_by_text("I don't understand how to use New Expensify.")
        ).to_be_visible()


        page.get_by_text("Next").click()


        page.get_by_role("textbox", name="Your response").fill("N/A")


        expect(page.get_by_role("textbox", name="Your response")).to_have_value("N/A")


        page.get_by_role("button", name="Next").click()


        page.get_by_role("button", name="Switch to Expensify Classic").click()

        try:

            with context.expect_page() as new_page_info:
                new_page = new_page_info.value


                assert (
                    new_page is not None
                ), "A new tab should have opened but it didn't."

        except PlaywrightTimeoutError:
            assert False, "Failed to open new tab after clicking the 'Switch to Expensify Classic' button."


        time.sleep(1)


        browser.close()
