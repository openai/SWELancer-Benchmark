import re
import time

from playwright.sync_api import Page, expect, sync_playwright


# Utility to generate a random email
# Don't use gmail as it has been ban
def generate_random_email(timestamp: int = int(time.time())):
    return f"turingtemp+{timestamp}@mustok{timestamp}.com"


def create_user(
    page: Page, firstname: str, lastname: str = None, timestamp: int = None
):
    timestamp = timestamp or int(time.time())
    # Sign up
    page.get_by_test_id("username").fill(generate_random_email())
    page.get_by_role("button", name="Continue").click()
    page.get_by_role("button", name="Join").click()

    # Update profile
    page.get_by_text("Track and budget expenses").click()
    page.get_by_role("textbox", name="First name").fill(firstname)
    page.get_by_role("textbox", name="Last name").fill(lastname)
    page.get_by_role("button", name="Continue").click()


def test_issue():

    with sync_playwright() as p:
        timestamp = int(time.time())

        # Launch chromium and open new page
        browser = p.chromium.launch(headless=False, slow_mo=500, args=["--disable-web-security", "--disable-features=IsolateOrigins, site-per-process"])
        context = browser.new_context()
        page = context.new_page()

        page.goto("https://dev.new.expensify.com:8082/")

        # create user
        create_user(page, "TestUser", "Surname", timestamp)

        page.get_by_label("Start chat (Floating action)").click()
        page.get_by_text("New workspace").click()
        page.get_by_role("button", name="Confirm").click()
        page.get_by_test_id("WorkspaceInitialPage").get_by_label(f"Mustok{timestamp}'s Workspace").click()
        page.get_by_label("Create").last.click()

        menu_items = page.locator('[role="menuitem"]')

        all_menu_texts = menu_items.all_text_contents()

        if all_menu_texts[0] == "Split expense":
            raise AssertionError(f"Test Failed! 'Split expense' is still the first item of the menu'")

        # ---------------------
        context.close()
    
        browser.close()

