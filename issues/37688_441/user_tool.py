import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from datetime import datetime
import time
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page
from utils.trace_cleaner import trace_cleaner

def generate_future_date_string():
    future_date = datetime(datetime.now().year + 1, 1, 1)
    return future_date.strftime("%Y-%m-%d")

TIMEOUT = 200000

def login_user(p, first_name="Milan", last_name="T", user_email=None):

    browser = p.chromium.launch(headless=True, args=[
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
        ], slow_mo=1000)
    
    context_args = {}
    context_args["timezone_id"] = "Asia/Dhaka"

    # Create context and start tracing
    context = browser.new_context()
    context.set_default_navigation_timeout(TIMEOUT)
    context.set_default_timeout(TIMEOUT)
    context.set_default_navigation_timeout(TIMEOUT)
    context.tracing.start(screenshots=True, snapshots=True, sources=True)

    page = context.new_page()

    page.goto("https://dev.new.expensify.com:8082/")

    page.locator('input[type="email"]').fill(user_email)
    page.get_by_role("button", name="Continue").click()

    page.get_by_role("button", name="Join").click()
    
    try:

        something_else_button = page.locator('div[aria-label="Something else"]')
        something_else_button.click()

        page.locator('input[name="fname"]').fill(first_name)
        page.locator('input[name="lname"]').fill(last_name)
        page.get_by_role("button", name="Continue").last.click()
    except:
        pass

    return browser, context, page, user_email


def test_banned_user_banner_appears_in_chat_instead_of_textbox():
    with sync_playwright() as p:
        # Initialize browser sessions
        browser, context, page, email = login_user(p, "User", "One", user_email="rgarciatammy4+1733074305@gmail.com")
        browser1, context1, page1, email1 = login_user(p, "User", "Two", user_email="rgarciatammy4+1733074306@gmail.com")
        
        try:
            start_chat_fab = page.get_by_role("button", name="Start chat (Floating action)")
            start_chat_fab.click()
            page.get_by_role("menuitem", name="Start chat").click()
            page.get_by_test_id("selection-list-text-input").fill(email1)
            page.get_by_label("User Two").click()
            chat_textbox = page.get_by_role("textbox")
            text_content = "This is a test message from an Expensify contributor! Please flag me as assault and block me."
            chat_textbox.fill(text_content)
            chat_textbox.press("Enter")
            page.wait_for_timeout(2000)


            page1.get_by_text("User Two").first.click()
            page1.get_by_text("User One").first.click()
            page1.get_by_text(text_content).hover()
            page1.get_by_label("Menu").click()
            page1.get_by_text("Flag as offensive").click()
            page1.get_by_label("Assault").get_by_text(
                "Message removed from channel"
            ).click()


            page.evaluate(
                """async (date) => {
                await Onyx.set('nvp_private_blockedFromChat', date);
            }""",
                generate_future_date_string(),
            )
            page.wait_for_timeout(3000)


            report_actions_view = page.get_by_test_id("report-actions-view-wrapper").last
            expect(report_actions_view).to_contain_text("Note: You've been banned from chatting in this channel")
        finally:
            # Stop tracing for the first browser context and export the trace
            trace_path1 = "/app/expensify/user_tool/output_browser1.zip"
            context.tracing.stop(path=trace_path1)
            trace_cleaner(trace_path1)
            browser.close()
            
            # Stop tracing for the second browser context and export the trace
            trace_path2 = "/app/expensify/user_tool/output_browser2.zip"
            context1.tracing.stop(path=trace_path2)
            trace_cleaner(trace_path2)
            browser1.close()


# If you want to run the test directly
if __name__ == '__main__':
    test_banned_user_banner_appears_in_chat_instead_of_textbox()
