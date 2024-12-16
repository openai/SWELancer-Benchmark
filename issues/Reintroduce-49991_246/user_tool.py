import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import re
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page


def login_user(p: PlaywrightContextManager, first_name="Milan", last_name="T") -> tuple[Browser, Page]:

    device = p.devices["Pixel 7"]
    browser = p.chromium.launch(
            channel="chrome",
            headless=True,
            args=[
                "--ignore-certificate-errors",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process"
            ],
            proxy={"server": "http://localhost:8080"},
            slow_mo=500
        )
    context = browser.new_context(
        timezone_id="Asia/Karachi", ignore_https_errors=True, **device
    )
    page = context.new_page()
    user_email = "freelanceapptest+1734178454@gmail.com" 

    page.goto('https://dev.new.expensify.com:8082/')
    page.get_by_test_id("username").fill(user_email)
    page.get_by_role("button", name="Continue").click()
    page.get_by_role("button", name="Join").click()

    try:
        expect(page.locator("text=What do you want to do today?")).to_be_visible()
        page.get_by_text("Track and budget expenses").click()
        page.get_by_role("button", name="Continue").click()
        page.get_by_role("textbox", name="First name").fill(first_name)
        page.get_by_role("textbox", name="Last name").fill(last_name)
        page.get_by_role("form").get_by_role("button", name="Continue").click()
    except:
        pass

    return browser, page 

def test_back_button():
    from utils.trace_cleaner import trace_cleaner
    with sync_playwright() as p:
        browser, page = login_user(p)
        context = page.context

        # Start tracing
        context.tracing.start(
            path="/app/expensify/user_tool/output_browser1.zip",
            screenshots=True,
            snapshots=True,
            sources=True
        )

        try:
            page.get_by_label("Back").click()
            page.get_by_label("Close").click()
            page.get_by_label("Start chat (Floating action)").click()
            page.get_by_text("Start chat").click()
            page.get_by_test_id("selection-list-text-input").fill("testuser@gmail.com")
            page.get_by_role("button", name="Add to group").click()
            page.get_by_role("button", name="Next").click()
            page.get_by_role("button", name="Start group").click()

            page.get_by_label("Create").click()
            page.get_by_text("Assign task").click()
            page.get_by_role("textbox", name="Title").fill("Test 1")
            page.get_by_role("button", name="Next").click()
            page.get_by_role("button", name="Confirm task").click()

            page.locator("div").filter(has_text=re.compile(r"^Test 1$")).nth(1).click()
            page.get_by_test_id("DisplayNamesWithTooltip").get_by_text("Test 1").click()
            page.get_by_label("Delete").click()
            page.get_by_role("button", name="Delete").click()
            page.get_by_role("button", name="Back").click()

            expect(page.get_by_test_id("lhn-options-list")).to_be_visible()
        except Exception as e:
            print(f"Error encountered: {e}")
            raise
        finally:
            # Stop tracing and clean it up
            context.tracing.stop()
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            browser.close()
