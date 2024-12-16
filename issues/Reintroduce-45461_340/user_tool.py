import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import Playwright, sync_playwright, expect
from utils.trace_cleaner import trace_cleaner

static_email = "testuserexpensify1+92@gmail.com"

def test_delete_expense_offline():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True, 
            slow_mo=1000, 
            args=["--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"], 
            proxy={"server":"http://localhost:8080"}
        )
        context = browser.new_context()
        # Start playwright tracing
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        try:
            page = context.new_page()
            page.goto("https://dev.new.expensify.com:8082/")
            page.get_by_test_id("username").click()
            page.get_by_test_id("username").fill(static_email)
            page.get_by_role("button", name="Continue").click()
            page.get_by_role("button", name="Join").click()
            page.get_by_label("Something else").click()
            page.get_by_role("textbox", name="First name").click()
            page.get_by_role("textbox", name="First name").fill("Test")
            page.get_by_role("textbox", name="Last name").click()
            page.get_by_role("textbox", name="Last name").fill("124")
            page.get_by_role("button", name="Continue").click()

            page.get_by_label("Start chat (Floating action)").click()
            page.get_by_text("Submit expense").click()
            page.get_by_label("Manual").click()
            page.get_by_placeholder("0").fill("2500")
            page.locator("#numPadContainerView").get_by_role("button", name="Next").click()
            page.get_by_test_id("selection-list-text-input").click()

            email = "hehe@gmaill.com"
            page.get_by_test_id("selection-list-text-input").fill(email)
            page.get_by_label(email).click()
            page.get_by_role("button", name="Submit").click()

            # Add random messages to the chat
            page.get_by_label("View details").click()
            page.get_by_role("textbox").click()
            page.get_by_role("textbox").fill("2")
            page.get_by_role("textbox").press("Enter")

            page.get_by_role("textbox").click()
            page.get_by_role("textbox").fill("3")
            page.get_by_role("textbox").press("Enter")

            page.get_by_role("textbox").click()
            page.get_by_role("textbox").fill("4")
            page.get_by_role("textbox").press("Enter")

            # Block all network requests
            context.set_offline(True)
            page.wait_for_timeout(3000)
            page.get_by_label(f"{email}").nth(1).click()
            page.get_by_label("Delete expense").click()
            page.get_by_role("button", name="Delete").click()

            element = page.locator("svg:nth-child(3) > rect")
            expect(element).to_be_hidden()

        finally:
            # Stop tracing and export
            context.tracing.stop()
            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            context.tracing.export(path=trace_path)
            trace_cleaner(trace_path)

            context.close()
            browser.close()
