from playwright.sync_api import sync_playwright, expect
from utils.trace_cleaner import trace_cleaner


def test_53668():
    with sync_playwright() as p:
        # Launch chromium and open new page
        browser = p.chromium.launch(headless=False, args=[
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ])
        context = browser.new_context()
        context.tracing.start(screenshots=True, snapshots=True, sources=True)

        try:
            page = context.new_page()
            page.goto("https://dev.new.expensify.com:8082/")
            page.locator('input[type="email"]').fill("ojidojdmwowjdoj@gmail.com")
            page.get_by_role("button", name="Continue").click()
            page.wait_for_timeout(9000)
            with page.expect_popup() as page1_info:
                page.get_by_role("link", name="here").click()
            page1 = page1_info.value
            page1.wait_for_timeout(3000)
            expect(page1.get_by_role("heading", name="Email Notifications")).to_be_visible()
        finally:
            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            browser.close()