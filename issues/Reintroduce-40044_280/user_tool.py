import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import Playwright, sync_playwright, expect
from utils.trace_cleaner import trace_cleaner

def test():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            channel="chrome", 
            headless=True, 
            args=["--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"],
            proxy={"server": "http://localhost:8080"},
            slow_mo=500
        )
        context = browser.new_context()

        # Start tracing
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        try:
            # Step 1: Go to page
            page = context.new_page()
            page.goto("https://dev.new.expensify.com:8082/")

            # Step 2: Open the URL again in a new tab
            page1 = context.new_page()
            page1.goto("https://dev.new.expensify.com:8082/")

            # Step 3: Switch back to page 1
            page.bring_to_front()
            expect(page.get_by_text("Another login page is open.")).to_be_visible(timeout=8000)

            # Trigger manual close behaviour
            page1.evaluate("window.dispatchEvent(new Event('beforeunload'));")
            page1.close()
            expect(page.get_by_text("Another login page is open.")).not_to_be_visible()
            expect(page.get_by_test_id("username")).to_be_visible()
        except Exception as e:
            # Reraise to mark the test as failed
            raise e
        finally:
            # Stop tracing and save the trace file
            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            context.tracing.stop(path=trace_path)

            # Clean the trace
            trace_cleaner(trace_path)
