import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from playwright._impl._page import Page
import pytest
import re


from utils.trace_cleaner import trace_cleaner

def login_user_if_not_logged_in(page: Page, first_name="Test", last_name="User"):

    page.goto('https://dev.new.expensify.com:8082/')

    email = "giwbpkqv+1735214762@gmail.com"

    page.get_by_test_id("username").fill(email)
    page.get_by_role('button', name="Continue").click()
    page.get_by_role('button', name="Join").click()

    try:
        expect(page.locator("text=What do you want to do today?")).to_be_visible()
        page.get_by_text("Track and budget expenses").click()
        page.get_by_role("button", name="Continue").click()
        page.get_by_role("textbox", name="First name").fill(first_name)
        page.get_by_role("textbox", name="Last name").fill(last_name)
        page.get_by_role("button", name="Continue").click()
    except:
        pass


def test_expensify_41523():
    with sync_playwright() as p:
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

        context = browser.new_context(timezone_id="Asia/Karachi")

        context.tracing.start(screenshots=True, snapshots=True, sources=True)

        page = context.new_page()
        test_email = "ztzvcilj+1735214758@gmail.com"

        try:

            login_user_if_not_logged_in(page, "Test", "User")

            for _ in range(2):
                page.get_by_label("Start chat (Floating action)").click()
                page.get_by_label("Submit expense").first.click()
                page.get_by_label("Manual").click()
                page.get_by_placeholder("0").fill("10")
                page.locator("#numPadContainerView").get_by_role("button", name="Next").click()
                page.get_by_test_id("selection-list-text-input").fill(test_email)
                page.get_by_test_id("selection-list").get_by_label(test_email).click()
                page.get_by_role("button", name=re.compile(r"Submit .+")).click()

            page.locator("button").filter(has_text=f"{test_email} owes: PKR 20.00").click()

            if page.get_by_label(test_email).nth(1).is_visible():
                print("Test Passed")
            else:
                pytest.fail("Chat header is not immediately visible")
        except Exception as e:

            raise e
        finally:

            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            context.tracing.stop(path=trace_path)
            trace_cleaner(trace_path)


        browser.close()
