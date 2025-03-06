import re
import time

from playwright.sync_api import Page, expect, sync_playwright


# Utility to generate a random email
def generate_email():
    return f"turingtemp+1739792303@gmail.com"


def create_user(
    page: Page, firstname: str, lastname: str = None, timestamp: int = None
):
    # Sign up
    page.get_by_test_id("username").fill(generate_email())
    page.get_by_role("button", name="Continue").click()
    page.get_by_role("button", name="Join").click()

    # Update profile
    page.get_by_text("Track and budget expenses").click()
    page.get_by_role("textbox", name="First name").fill(firstname)
    page.get_by_role("textbox", name="Last name").fill(lastname)
    page.get_by_role("button", name="Continue").click()


def test_issue():

    with sync_playwright() as p:

        # Launch chromium and open new page
        browser = p.chromium.launch(headless=False, slow_mo=500, args=[ "--disable-web-security", "--disable-features=IsolateOrigins, site-per-process"])
        context = browser.new_context()
        page = context.new_page()

        page.goto("https://dev.new.expensify.com:8082/")

        try:
            # create user
            create_user(page, "TestUser", "Surname")
        except:
            pass

        page.get_by_label("My settings").click()
        page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").get_by_text("Workspaces").click()
        page.get_by_label("New workspace").click()
        page.locator('div[role="menuitem"][aria-label$="Workspace"]').click()
        page.get_by_role("textbox", name="Name").fill("Random 1 Workspace")
        page.get_by_role("button", name="Save").click()
        page.get_by_label("Back").click()
        page.get_by_label("Inbox").click()
        page.get_by_label("My settings").click()
        page.get_by_label("Preferences").click()
        page.locator("div").filter(has_text=re.compile(r"^English$")).first.click()
        page.get_by_label("Spanish").click()
        page.get_by_label("Recibidos").click()

        spanish_text = page.get_by_text("Úsalo para hablar sobre la")
        expect(spanish_text).to_be_visible()

        # ---------------------
        context.close()
        browser.close()

