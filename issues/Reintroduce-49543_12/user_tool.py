import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page

from utils.trace_cleaner import trace_cleaner


def login_user(p: PlaywrightContextManager) -> tuple[Browser, Page]:

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

    context = browser.new_context(timezone_id = "Asia/Karachi")
    page = context.new_page()

    user_email = "testemail.ameen+49543@gmail.com"

    page.goto('https://dev.new.expensify.com:8082/') 

    page.get_by_test_id("username").fill(user_email)
    page.get_by_role("button", name="Continue").click()
    page.get_by_test_id("validateCode").fill("123456")

    return browser, page


def test_check_tag_rules():
    with sync_playwright() as p:
        browser, page = login_user(p)
        context = page.context
        trace_path = "/app/expensify/user_tool/output_browser1.zip"
        
        # Start tracing
        context.tracing.start(screenshots=True, snapshots=True, sources=True)

        try:
            page.get_by_label("My settings").click()
            page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()
            page.get_by_label("row").click()
            page.get_by_label("Tags").click()
            page.get_by_label("State", exact=True).click()
            page.locator("#CA").click()

            assert not (
                page.locator("text=Tag rules").is_visible() or page.locator("text=Approver").is_visible()
            ), "Fail: 'Tag rules' or 'Approver' text is present in Tag Settings."
        finally:
            # Stop and export the trace, then clean it
            context.tracing.stop()
            context.tracing.export(trace_path)
            trace_cleaner(trace_path)
            browser.close()
