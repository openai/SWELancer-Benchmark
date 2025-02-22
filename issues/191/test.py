import time
import re
from playwright.sync_api import sync_playwright, expect, Page


def get_test_user_info(seed=None, first_name=None, last_name=None):
    if first_name is None:
        first_name = "D"

    if last_name is None:
        last_name = "C"

    if seed is None:
        seed = time.time()
    email = f"{seed}@e.co"
    
    return {
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
    }


def login_user(page: Page, user_info):
    page.goto('https://dev.new.expensify.com:8082/')
    page.wait_for_load_state('load')

    page.get_by_test_id("username").fill(user_info["email"])
    page.get_by_role("button", name="Continue").click()
    page.get_by_role("button", name="Join").click()


def onboarding_user(page: Page, user_info: dict[str, str]):
    expect(page.get_by_text("What do you want to do today?")).to_be_visible(timeout=30000)
    
    # Select 'Track and budget expenses' in onboarding page and click Continue
    activity_text = "Track and budget expenses"
    page.get_by_label(activity_text).click()
    page.get_by_role("button", name="Continue").click()

    # Enter first name, last name and click continue
    page.get_by_role("textbox", name="First name").fill(user_info["first_name"])
    page.get_by_role("textbox", name="Last name").fill(user_info["last_name"])
    page.get_by_role("button", name="Continue").last.click()


def test_issue_51028():
    with sync_playwright() as p:
        # Launch chromium in mobile emulation (Android) mode
        browser = p.chromium.launch(headless = False, args = ["--no-sandbox", "--disable-dev-shm-usage", "--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"], channel = "chromium")
        
        # Ensure context uses device emulation
        context = browser.new_context()
        
        page = context.new_page()

        user_info = get_test_user_info(seed=123456, first_name="Alice")
        
        # Login
        login_user(page, user_info)
        onboarding_user(page, user_info)
        
        # Search and filter functionality
        page.get_by_label("Search").click()
        page.get_by_role("button", name="Filters").click()
        page.get_by_text("Report ID").click()
        page.get_by_role("textbox", name="Report ID").fill("1234")
        page.get_by_role("button", name="Save").click()
        page.get_by_role("button", name="Save search").click()
        
        # Navigate to saved searches and delete one
        page.get_by_label("More").click()
        page.get_by_test_id("SearchPageBottomTab").get_by_text("Saved").click()
        page.get_by_label("More").click()
        page.get_by_text("Delete").click()
        page.get_by_role("button", name="Delete").click()
        
        # Verify that the saved search is not visible anymore
        assert not (page.get_by_text("Saved")).is_visible(), "The saved text appears for a couple of seconds after the filter was deleted"

        # ---------------------
        context.close()
        browser.close()
