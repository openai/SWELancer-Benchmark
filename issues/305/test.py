import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import os

from playwright.sync_api import sync_playwright

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


        page = context.new_page()
        page.goto(NEW_DOT_URL)


        page_1 = context.new_page()
        page_1.goto(NEW_DOT_URL)


        page.bring_to_front()
        page.wait_for_timeout(3000)


        page_1.evaluate("window.dispatchEvent(new Event('beforeunload'));")
        page_1.close()

        visible = False
        if page.locator("text=Get started below.").is_visible():
            visible = True

        assert visible, "The text 'Get started below.' should be visible."
