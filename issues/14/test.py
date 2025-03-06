import time
from playwright.sync_api import expect, sync_playwright

NEW_DOT_URL = "https://dev.new.expensify.com:8082/"
WORKSPACE_NAME = "test"
FIRST_NAME = "Test"
SECOND_NAME = "Test"


# Utility to generate a random email
def generate_random_email():
    timestamp = 123456
    return f"testuser+{timestamp}@gmail.com"


def create_user(page, firstname, lastname):
    page.goto(NEW_DOT_URL)
    page.get_by_test_id("username").fill(generate_random_email())
    page.get_by_role("button", name="Continue").click()
    page.get_by_role("button", name="Join").click()
    page.get_by_text("Track and budget expenses").click()
    page.get_by_role("textbox", name="First name").fill(firstname)
    page.get_by_role("textbox", name="Last name").fill(lastname)
    page.get_by_role("button", name="Continue").click()
    page.wait_for_timeout(1000)


def create_new_workspace(page): 
    page.get_by_label("My settings").click()
    page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()
    page.get_by_role("button",name = "New workspace").first.click()
    page.get_by_test_id("WorkspacePageWithSections").get_by_text("Name").click()
    page.get_by_role("textbox", name="Name").fill(WORKSPACE_NAME)
    page.get_by_role("button", name="Save").click()
    page.get_by_label("Back").first.click()
    page.get_by_label("Inbox").click()


def delete_workspace(page):
    page.get_by_label("My settings").click()
    page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()
    page.get_by_role("button", name="More").click()
    page.get_by_test_id("PopoverMenuItem-Delete workspace").click()
    page.get_by_label("Delete").click()
    page.get_by_label("Inbox").click()


def track_expense(page):
    page.get_by_test_id("lhn-options-list").get_by_text(f"{FIRST_NAME} {SECOND_NAME} (you)").click()
    page.get_by_role("button", name="Create").click()
    page.locator('[data-testid="PopoverMenuItem-Create expense"], [data-testid="PopoverMenuItem-Track expense"]').first.click()
    page.get_by_label("Manual").click()
    page.get_by_placeholder("0").fill("80")
    page.locator("#numPadContainerView").get_by_role("button", name="Next").click()
    page.get_by_role("button", name="Track expense").click()
    page.get_by_role("button", name="Categorize it").click()
    expect(page.get_by_text("Upgrade to the Control plan")).to_be_visible()


def test_expensify_analysis_54864():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless = False, args = ["--no-sandbox", "--disable-dev-shm-usage", "--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"], slow_mo = 500, channel = "chromium")
        context = browser.new_context()
        page = context.new_page()
        create_user(page, FIRST_NAME, SECOND_NAME)
        create_new_workspace(page)
        delete_workspace(page)
        track_expense(page)

        context.close()
        browser.close()
