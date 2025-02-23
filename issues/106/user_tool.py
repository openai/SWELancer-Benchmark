import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright
from utils.trace_cleaner import trace_cleaner

def test_offline_message_not_visible_when_online():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=[
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
        ])
        context = browser.new_context()

        context.tracing.start(title="trace", snapshots=True, screenshots=True, sources=True)
        page = context.new_page()

        try:

            page.goto("https://dev.new.expensify.com:8082/")


            page.context.set_offline(False)


            page.wait_for_timeout(2000)  # Add a short delay to ensure the page has updated its state


            offline_message = page.locator("text=You appear to be offline")


            assert offline_message.count() == 0, "The offline message should not be visible when online"
        except Exception:

            raise
        finally:

            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")

            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")

            browser.close()