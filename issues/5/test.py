import re
import time

from playwright.sync_api import Page, expect, sync_playwright


# Utility to generate a random email
def generate_email():
    timestamp = int(time.time())
    return f"turingtemp+1740078308@gmail.com"


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
        browser = p.chromium.launch(headless=False, args=[
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ], slow_mo=500)
        context = browser.new_context()
        page = context.new_page()

        page.goto("https://dev.new.expensify.com:8082/")

        try:
            create_user(page, "TestUser", "Surname")
        except:
            pass

        page.get_by_label("Start chat (Floating action)").click()
        page.get_by_text("New workspace").click()
        
        workspace_name = f"TestUser Surname's Workspace"
        page.get_by_test_id("WorkspaceInitialPage").get_by_label(workspace_name).get_by_text(workspace_name).click()
        page.get_by_label("Create").last.click()
        page.get_by_text("Create expense").click()
        page.get_by_label("Manual").click()
        page.get_by_placeholder("0").fill("288")
        page.locator("#numPadContainerView").get_by_role("button", name="Next").click()
        page.get_by_text("Required").click()
        page.get_by_role("textbox", name="Merchant").fill("shawne")
        page.get_by_role("button", name="Save").click()
        page.get_by_role("button", name=re.compile(r"Create ₹\d+\.\d{2} expense")).click()
        page.get_by_label("View details").click()
        page.locator(
            "div:nth-child(2) > div > div > div > div > div > div > div > div > div > div > div > div > div > div > div > div > div > div:nth-child(2) > button"
        ).click()
        page.get_by_text(re.compile(r"Pay ₹\d+\.\d{2} elsewhere")).click()
        page.get_by_role("button", name=re.compile(r"Pay ₹\d+\.\d{2} elsewhere")).click()
        page.get_by_label(workspace_name).nth(1).click()
        page.get_by_text("Cancel payment").click()
        page.get_by_role("button", name="Cancel payment").click()

        cancellation_message = page.get_by_test_id("customer-ReportActionsList").get_by_text(
            re.compile(r"canceled the ₹\d+\.\d{2} payment")
        )
        
        expect(cancellation_message).to_be_visible()

        # ---------------------
        context.close()
        browser.close()
