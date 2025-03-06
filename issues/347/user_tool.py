import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page

from utils.trace_cleaner import trace_cleaner


def generate_random_email():
    task_number = 28265
    return f"checkissue+{task_number}@gmail.com"


def login_user(p: PlaywrightContextManager, first_name="Milan", last_name="T") -> tuple[Browser, Page, str]:

    browser = p.chromium.launch(headless=True, args=["--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"],
    proxy={"server": "http://localhost:8080"},
    slow_mo=500)
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    user_email = generate_random_email()


    page.goto('https://dev.new.expensify.com:8082/') 


    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(2000)


    try: 
        page.locator('button[tabindex="0"]').click()
        page.wait_for_timeout(2000)
    except Exception:
        pass


    expect(page.locator("text=What do you want to do today?")).to_be_visible()
        

    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()


    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()
    page.wait_for_timeout(2000)

    return browser, page, context, user_email


def test_spanish_emoji_text():
    with sync_playwright() as p:
        browser, page, context, user_email = login_user(p)

        context.tracing.start(
            screenshots=True,
            snapshots=True,
        )
        try:
            page.wait_for_timeout(1000)


            page.locator('span:text("Milan T (you)")').click()
            page.wait_for_timeout(1000)
            page.get_by_role("textbox").click()
            page.wait_for_timeout(1000)


            page.get_by_role("textbox").fill("Hi :rosa:")
            page.wait_for_timeout(1000)


            page.get_by_label("My settings").click()
            page.wait_for_timeout(1000)
            page.get_by_text("Preferences").click()
            page.wait_for_timeout(1000)
            page.get_by_text("Language").click()
            page.wait_for_timeout(1000)
            page.get_by_label("Spanish").click()
            page.wait_for_timeout(1000)


            page.get_by_label("Recibidos").click()
            page.wait_for_timeout(2000)


            expect(page.get_by_text("🌹", exact=True)).to_be_visible()

        except Exception as e:

            raise e
        finally:

            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")

            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")

            browser.close()
