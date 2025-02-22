import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
import pytest
import random
from playwright.sync_api import sync_playwright, Page


from utils.trace_cleaner import trace_cleaner



def generate_random_email():
    timestamp = int(time.time())
    return f"kenworktestemail+993@gmail.com"



def generate_random_name():
    first_names = ["John", "Jane", "Alex", "Emily", "Chris", "Sam", "Max", "Taylor"]
    last_names = [
        "Smith",
        "Doe",
        "Johnson",
        "Williams",
        "Brown",
        "Davis",
        "Miller",
        "Wilson",
    ]
    return random.choice(first_names), random.choice(last_names)


@pytest.fixture
def setup_playwright():

    playwright = sync_playwright().start()

    browser = playwright.chromium.launch(
        headless=True, args=["--ignore-certificate-errors", "--disable-web-security",
        "--disable-features=IsolateOrigins, site-per-process"]
    )

    context = browser.new_context()
    page = context.new_page()
    yield page
    context.close()
    browser.close()
    playwright.stop()



def login_user(page: Page, email: str, first_name: str, last_name: str):
    page.goto("https://dev.new.expensify.com:8082/")
    page.locator('input[type="email"]').fill(email)
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(1000)

    try:
        page.locator('button[tabindex="0"]').click()
        page.wait_for_timeout(1000)
    except Exception:
        pass
    if page.get_by_text("Track and budget expenses").is_visible():
        page.locator("text='Track and budget expenses'").click()
        page.get_by_role("button", name="Continue").click()
        page.wait_for_timeout(1000)

        page.locator('input[name="fname"]').fill(first_name)
        page.locator('input[name="lname"]').fill(last_name)
        page.get_by_role("button", name="Continue").last.click()
        page.wait_for_timeout(1000)



def create_workspace(page: Page):
    page.locator('button[aria-label="Workspaces"]').click()
    page.wait_for_timeout(1000)
    page.get_by_test_id("WorkspaceSwitcherPage").get_by_role(
        "button", name="New workspace"
    ).click()
    page.locator('button[aria-label="Back"]').click()
    page.wait_for_timeout(1000)
    page.locator('button[aria-label="Back"]').click()
    page.wait_for_timeout(1000)


@pytest.mark.usefixtures("setup_playwright")
def test_lhn_workspace(setup_playwright):
    page = setup_playwright
    context = page.context
    trace_path = "/app/expensify/user_tool/output_browser1.zip"


    context.tracing.start(screenshots=True, snapshots=True, sources=True)

    try:
        email = generate_random_email()
        first_name, last_name = generate_random_name()
        workspace_name = f"{email}'s Workspace"

        login_user(page, email, first_name, last_name)
        create_workspace(page)

        page.wait_for_timeout(2000)
        try:
            lhn_workspace_text = page.locator(
                'button[aria-label="Navigates to a chat"]', has_text=workspace_name
            ).inner_text()
        except Exception:
            lhn_workspace_text = (
                page.locator(
                    'button[aria-label="Navigates to a chat"]', has_text=workspace_name
                )
                .nth(0)
                .inner_text()
            )

        assert (
            "No activity yet" not in lhn_workspace_text
        ), "'No activity yet' is shown for workspace in LHN!"

    except Exception as e:

        raise e

    finally:

        context.tracing.stop(path=trace_path)
        trace_cleaner(trace_path)
