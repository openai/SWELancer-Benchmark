import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright._impl._page import Page
from playwright.sync_api import sync_playwright, expect
import time

from utils.trace_cleaner import trace_cleaner  # <-- Added import

NEWDOT_URL = "https://dev.new.expensify.com:8082/"
EMAIL = "checkissue77+41510@gmail.com"


def new_dot_login(page: Page, email: str) -> None:
    page.goto(NEWDOT_URL)
    page.locator('input[type="email"]').fill(email)

    continue_button = page.get_by_role("button", name="Continue")
    continue_button.click()

    join_button = page.get_by_role("button", name="Join")
    join_button.click()


def enter_user_information(page: Page) -> None:
    track_expenses_text = page.get_by_text("Track and budget expenses")
    track_expenses_text.click()

    page.get_by_role("textbox", name="First name").fill("Test")

    page.get_by_role("textbox", name="Last name").fill("User")

    continue_button_after_names = page.get_by_role("button", name="Continue")
    continue_button_after_names.click()


def task_check(page: Page) -> None:
    # Step 2: create task to asign
    page.get_by_label("Start chat (Floating action)").click()

    # Click on "Start chat" button
    page.get_by_label("Start chat", exact=True).click()

    # Input the email another person
    expect(page.get_by_test_id("selection-list-text-input")).to_be_visible()
    page.get_by_test_id("selection-list-text-input").fill("test1@gmail.com")

    # Add User to the chat
    expect(page.get_by_role("button", name="Add to group")).to_be_visible()
    page.get_by_role("button", name="Add to group").click()
    page.get_by_role("button", name="Next").click()  # Click on "Next" button

    expect(page.get_by_role("button", name="Start group")).to_be_visible()
    page.get_by_role("button", name="Start group").click()

    page.get_by_label("Create").last.click()
    page.get_by_label("Assign task").click()

    # Step 3: Enter the test task
    page.get_by_role("textbox", name="Title").fill("Test task")
    page.get_by_role("button", name="Next").click()

    # Step 4: Select assignee and check if the test assign to me is visible
    page.get_by_role("menuitem", name="Assignee").click()
    expect(page.get_by_text("Assign to me")).to_be_visible()


def test_expensify_0000() -> None:
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
            slow_mo = 1000
        )

        context_args = {
            "timezone_id": "America/Los_Angeles",
        }

        context = browser.new_context(**context_args)
        # Start tracing
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        try:
            page = context.new_page()

            new_dot_login(page, EMAIL)
            enter_user_information(page)
            task_check(page)
        except Exception as e:
            # Ensure trace is still saved if test fails
            raise e
        finally:
            # Stop tracing and save it
            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            context.tracing.stop(path=trace_path)
            # Clean the trace
            trace_cleaner(trace_path)

            context.close()
            browser.close()
