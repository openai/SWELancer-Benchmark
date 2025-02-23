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
    timestamp = int(time.time())
    return f"turingtemp+994508@gmail.com"


def login_user(p: PlaywrightContextManager, first_name="Milan", last_name="T") -> tuple[Browser, Page, str]:

    browser = p.chromium.launch(headless=True, args=[
        "--disable-web-security",
        "--disable-features=IsolateOrigins,site-per-process"
    ])
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    user_email = generate_random_email()


    page.goto('https://dev.new.expensify.com:8082/')


    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(2000)


    try:
        page.locator('button[tabindex="0"]').click()
        page.wait_for_timeout(4000)
    except Exception:
        pass

    try:
        expect(page.locator("text=What do you want to do today?")).to_be_visible()
        

        page.locator("text='Track and budget expenses'").click()
        page.get_by_role("button", name="Continue").click()
        

        page.locator('input[name="fname"]').fill(first_name)
        page.locator('input[name="lname"]').fill(last_name)
        page.get_by_role("button", name="Continue").last.click()
        page.wait_for_timeout(2000)
    except:
        pass

    return browser, page, context, user_email


def test_emojiart():
    with sync_playwright() as p:
        browser, page, context, user_email = login_user(p)

        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        try:

            page.get_by_label("Start chat (Floating action)").click()
            page.get_by_text("Start chat").click()
            page.wait_for_timeout(3000)
            page.get_by_label("Milan T (you)").last.click()
            page.get_by_role("textbox").fill("💙💗💗💗💗💗💗\n💙❤❤❤❤❤  💛💗\n💙❤HELLO ♪❤💛💗\n💙❤👍☀👎❤ 💛💗\n💙❤☮ O˥˥ƎH❤💛💗\n💙❤❤❤❤❤   💛💗\n💚💚💚💚💚💚💛\n")
            page.keyboard.press("Enter")


            page.get_by_label("Emoji").nth(1).click()
            page.wait_for_timeout(2000)

            crash_message = "Uh-oh, something went wrong!"
            assert crash_message not in page.content(), f"Crash message '{crash_message}' was found on the page"
        except Exception as e:
            raise e
        finally:

            context.tracing.stop()
            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            context.tracing.export(path=trace_path)

            trace_cleaner(trace_path)
