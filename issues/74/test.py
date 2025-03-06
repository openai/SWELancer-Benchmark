import time
from email import message_from_bytes
from email.header import decode_header
import re

import pytest
from playwright._impl._page import Page
from playwright.sync_api import expect, sync_playwright
from playwright.sync_api._context_manager import PlaywrightContextManager


def get_test_user_info(first_name: str = "Test", last_name: str = "User"):
    
    timestamp = int(time.time())
    email = f"test+{timestamp}@gmail.com"

    return {
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
    }


def select_activity(page, first_name, last_name, activity_text):
    """
    Selects an activity on the page based on the provided activity text and user details.

    Args:
        page (Page): The Playwright Page object to interact with.
        first_name (str): The first name of the user.
        last_name (str): The last name of the user.
        activity_text (str): The text of the activity to select.

    Returns:
        None
    """

    # Select activity in onboarding page and click Continue
    page.get_by_label(activity_text).click()

    # Enter first name, last name and click continue
    page.get_by_role("textbox", name="First name").fill(first_name)
    page.get_by_role("textbox", name="Last name").fill(last_name)
    page.get_by_role("button", name="Continue").last.click(force=True)


def signup_user(
    page: Page, user_info: dict, activity_text: str = "Track and budget expenses"
):
    
    page.goto("https://dev.new.expensify.com:8082/", timeout=90000)
    page.wait_for_load_state("load")

    page.locator('input[type="email"]').fill(user_info["email"])
    page.locator("button", has_text="Continue").click()
    page.wait_for_timeout(1500)

    if page.get_by_role("button", name="Join").is_visible():
        page.get_by_role("button", name="Join").click()
    else:
        magic_code = "123456"  # get_magic_code(
        # user_info["email"], user_info["password"], retries=6, delay=5
        # )

        page.locator('input[data-testid="validateCode"]').fill(magic_code)

    page.wait_for_timeout(3000)

    activity_dialog: int = len(
        page.query_selector_all("text=What do you want to do today?")
    )

    if activity_dialog > 0:
        select_activity(
            page, user_info["first_name"], user_info["last_name"], activity_text
        )



def test_click_pay():
    with sync_playwright() as p:
        # Get test user info
        user_info = get_test_user_info()

        # Create browser context and page
        # Launch browser
        browser = p.chromium.launch(proxy = {"server": "http://localhost:8080"}, headless = False, args = ["--no-sandbox", "--disable-dev-shm-usage", "--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"], slow_mo = 500, channel = "chromium")
    
        iphone_14_pro = p.devices["iPhone 14 Pro"]
        context = browser.new_context(**iphone_14_pro)
        page = context.new_page()

        signup_user(page, user_info)
        page.get_by_label("Back").click()
        page.get_by_label("My settings").click()
        page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").get_by_text("Workspaces").click()
        page.get_by_label("New workspace").click()
        page.get_by_test_id("WorkspaceInitialPage").get_by_label("Back").click()
        page.get_by_label("Back").click()
        page.get_by_label("Inbox").click()
        page.get_by_text("Test User's Workspace").nth(0).click()
        page.get_by_label("Create").click()
        try:
            page.get_by_text("Create Expense").click(timeout = 2000)
        except:
            page.get_by_text("Submit expense", exact=True).click()
        page.get_by_label("Manual").click()
        page.get_by_placeholder("0").fill("100")
        page.locator("#numPadContainerView").get_by_role("button", name="Next").click()
        page.get_by_text("Merchant").click()
        page.get_by_role("textbox", name="Merchant").fill("aa")
        page.get_by_role("button", name="Save").click()
        page.get_by_role("button", name=re.compile(r"^Submit")).nth(0).click()
        page.locator("#composer").click()
        page.locator("#composer").fill("hello")
        page.get_by_label("Send").click()
        page.locator("div").filter(has_text=re.compile(r"^hello$")).nth(4).click(button="right")
        page.get_by_text("Edit comment").click()
        page.get_by_test_id("report-actions-list").locator("#composer").fill("hellosfd")
        page.get_by_label("View details").get_by_role("button").nth(1).click()
        assert page.get_by_text(re.compile(r"100\.00 elsewhere$")).is_visible()
