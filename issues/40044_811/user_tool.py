import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import os
from playwright.sync_api import sync_playwright
from utils.trace_cleaner import trace_cleaner

NEW_DOT_URL = "https://dev.new.expensify.com:8082/"
PROXY_URL = os.getenv("PROXY_URL")
SLOW_MO: int | None = 500


def test():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            slow_mo=SLOW_MO,
            proxy={"server": PROXY_URL} if PROXY_URL else None,
            args=[
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
            ],
        )
        context = browser.new_context()

        # Start Playwright tracing
        context.tracing.start(
            screenshots=True,
            snapshots=True,
            sources=True
        )

        try:
            # Step 1: Go to page
            page = context.new_page()
            page.goto(NEW_DOT_URL)

            # Step 2: Open the URL again in a new tab
            page_1 = context.new_page()
            page_1.goto(NEW_DOT_URL)

            # Step 3: Switch back to page 1
            page.bring_to_front()
            page.wait_for_timeout(3000)

            # Trigger manual close behaviour
            page_1.evaluate("window.dispatchEvent(new Event('beforeunload'));")
            page_1.close()

            visible = False
            if page.locator("text=Get started below.").is_visible():
                visible = True

            assert visible, "The text 'Get started below.' should be visible."
        except Exception as e:
            # The test failed, but we'll still stop trace and clean up
            raise e
        finally:
            # Stop tracing and save trace to a file
            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            # Clean the trace
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
