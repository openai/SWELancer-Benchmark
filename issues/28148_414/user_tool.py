import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import re
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page
from utils.trace_cleaner import trace_cleaner


def login_user(p: PlaywrightContextManager, first_name="Ayush", last_name="G") -> tuple[Browser, Page, str]:

    browser = p.chromium.launch(
        headless=True, 
        args=[
            "--ignore-certificate-errors",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ],
        slow_mo=500
    )
    context = browser.new_context()
    page = context.new_page()
    user_email = "zfhmkgsf+1733658447@gmail.com"

    page.goto('https://dev.new.expensify.com:8082/') 

    page.get_by_test_id("username").fill(user_email)
    page.get_by_role("button", name="Continue").click()
    page.get_by_role("button", name="Join").click()

    try:
        expect(page.locator("text=What do you want to do today?")).to_be_visible()
        page.get_by_text("Track and budget expenses").click()
        page.get_by_role("textbox", name="First name").fill(first_name)
        page.get_by_role("textbox", name="Last name").fill(last_name)
        page.get_by_role("button", name="Continue").click()
    except:
        pass

    return page, context


def test_save_description_in_submitted_expense():
    with sync_playwright() as p:
        page, context = login_user(p)
        trace_path = "/app/expensify/user_tool/output_browser1.zip"
        try:
            context.tracing.start(screenshots=True, snapshots=True, sources=True)

            # Test logic
            context.set_offline(True)

            page.get_by_label("My settings").click()
            page.locator("div").filter(has_text=re.compile(r"^Ayush G$")).nth(2).click()
            page.get_by_role("textbox", name="First name").fill("Ayush1")

            save_button = page.locator('button div:text("Save")')
            save_button.click()

            change_display_name_text = page.locator('div:text("Your display name is shown on your profile.")')
            expect(change_display_name_text).to_be_hidden()

        except Exception as e:
            raise e
        finally:
            context.tracing.stop(path=trace_path)
            trace_cleaner(trace_path)
