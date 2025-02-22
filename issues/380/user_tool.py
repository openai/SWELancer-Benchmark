import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
import random
import re
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page
from utils.trace_cleaner import trace_cleaner


def generate_random_email():
    return "redx224+6856@gmail.com"


def login_user(p: PlaywrightContextManager, first_name="Milan", last_name="T") -> tuple[Browser, Page, str]:

    browser = p.chromium.launch(channel="chrome", headless=True, args=[
        "--disable-web-security",
        "--disable-features=IsolateOrigins,site-per-process"
    ])
    context = browser.new_context()


    context.tracing.start(screenshots=True, snapshots=True, sources=True)

    page = context.new_page()
    user_email = generate_random_email()


    page.goto('https://dev.new.expensify.com:8082/')


    page.locator('input[type="email"]').fill(user_email)
    page.get_by_role("button", name="Continue").click()


    page.get_by_role("button", name="Join").click()

    page.wait_for_selector("text=What do you want to do today?")
    expect(page.locator("text=What do you want to do today?")).to_be_visible()


    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()
    page.wait_for_timeout(500)


    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()
    page.wait_for_timeout(500)


    return browser, page, user_email


def test_issue_18909():
    with sync_playwright() as p:
        browser, page, user_email = login_user(p)

        context = page.context
        try:
            own_chat = page.get_by_text("Milan T (you)")
            expect(own_chat).to_be_visible()
            own_chat.click()
            page.wait_for_timeout(500)

            emoji = page.locator('div[aria-label="Emoji"]').nth(1)
            expect(emoji).to_be_visible()
            emoji.click()
            page.wait_for_timeout(500)

            page.locator('input[aria-label="Search"]').nth(0).fill("avsfb")
            test = page.locator("div").filter(has_text=re.compile(r"^Search$")).first
            page.wait_for_timeout(500)
            expect(test).to_have_css("padding", "8px 16px 12px")
        except Exception as e:

            raise e
        finally:

            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")

            browser.close()
