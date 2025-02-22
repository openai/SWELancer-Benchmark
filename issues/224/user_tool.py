import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
from playwright._impl._page import Page
from playwright.sync_api import sync_playwright
from utils.trace_cleaner import trace_cleaner

first_name = "Alice"
last_name = "Aliceoglu"
workspace_name = "Jellystarfish99+430043@gmail.com's Workspace"


def generate_random_email():
    number = "493371"
    return f"aliceoglualice+{number}@gmail.com"

def login_user(page: Page) -> None:

    username_input = page.get_by_test_id("username")
    username_input.click()

    username_input.fill(generate_random_email())

    continue_button = page.get_by_role("button", name="Continue")
    continue_button.click()
    

    join_button = page.get_by_role("button", name="Join")
    join_button.click()
    

def enter_user_information(page:Page) -> None:

    track_expenses_text = page.get_by_text("Track and budget expenses")
    track_expenses_text.click()


    first_name_input = page.get_by_role("textbox", name="First name")
    first_name_input.fill(first_name)

    first_name_input.press("Tab")

    last_name_input = page.get_by_role("textbox", name="Last name")
    last_name_input.fill(last_name)
    

    continue_button_after_names = page.get_by_role("button", name="Continue")
    continue_button_after_names.click()

def reproduce_scenario(page: Page) -> None:
    page.get_by_label("My settings").click()
    page.get_by_label("Status").click()
    page.get_by_role("button", name="Save").dblclick()
    page.wait_for_timeout(5000)
    assert not page.get_by_label("Create").is_visible(), "The 'Create' button is unexpectedly visible"
    
def test_room_name_is_highlighted() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=["--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"])
        context = browser.new_context(ignore_https_errors=True)

        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        try:
            page = context.new_page()
            page.goto("https://127.0.0.1:8082/")


            login_user(page)


            if page.get_by_text("What do you want to do today?").is_visible():
                enter_user_information(page)


            reproduce_scenario(page)
        except Exception as e:

            raise e
        finally:

            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            context.tracing.stop(path=trace_path)

            trace_cleaner(trace_path)

            context.close()
            browser.close()
