import re
from playwright.sync_api import Playwright, sync_playwright, expect
import time

def get_mail_addr():
    timestamp = int(time.time())
    return f"aliceogleoggglu+{timestamp}@gmail.com"

def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False, args=[
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
            "--ignore-certificate-errors"],slow_mo=800)
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()

    # Step 1: Login
    user_mail_addr = get_mail_addr()
    user_ws_name = "Ali veli's Workspace"
    page.goto("https://dev.new.expensify.com:8082/")
    page.get_by_test_id("username").click()
    page.get_by_test_id("username").fill(user_mail_addr)
    page.get_by_role("button", name="Continue").click()
    page.get_by_role("button", name="Join").click()
    page.wait_for_timeout(1000)
    
    # Step 2: Enter user information
    page.get_by_text("Track and budget expenses").click()
    page.get_by_role("textbox", name="First name").fill("ali")
    page.get_by_role("textbox", name="First name").press("Tab")
    page.get_by_role("textbox", name="Last name").fill("veli")
    page.get_by_role("button", name="Continue").click()
    page.wait_for_timeout(1000)
    
    # Step 3: Create WS
    page.get_by_label("My settings").click()
    page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").get_by_text("Workspaces").click()
    page.get_by_label("New workspace").click()
    page.get_by_label("Back").click()
    page.get_by_label("Inbox").click()
    page.locator("div[dir='auto']", has_text="ali veli (you)").first.click()
    page.wait_for_timeout(1000)

    # Step 4: Submit Expense
    page.get_by_label("Create").last.click()
    try:
        page.get_by_text("Create expense").click()
    except:
        page.get_by_text("Track expense").click()
    page.get_by_label("Manual").click()
    page.get_by_placeholder("0").fill("123")
    page.locator("#numPadContainerView").get_by_role("button", name="Next").click()
    page.wait_for_timeout(500)
    page.get_by_role("button", name="Track expense").click()
    page.wait_for_timeout(1000)

    # Step 5: Check in search page
    page.get_by_test_id("CustomBottomTabNavigator").get_by_label("Search").click()
    page.locator("div[dir='auto']", has_text="123.00").last.click()
    page.locator("div[dir='auto']", has_text="Tracking").last.click()
    page.get_by_test_id("ReportDetailsPage").get_by_text("Share it with my accountant").click()
    page.wait_for_timeout(500)
    page.get_by_test_id("IOURequestStepParticipants").get_by_label(user_ws_name).click()
    page.wait_for_timeout(500)
    page.get_by_test_id("IOURequestStepConfirmation").get_by_label(user_ws_name).click()
    page.wait_for_timeout(500)
    page.get_by_role("button", name="Back").click()
    page.wait_for_timeout(500)


    # Step 6: Verify the show more button is visible 
    show_more_button = page.get_by_label("Show more")
    expect(show_more_button).to_be_visible()

    create_button = page.locator("button[aria-label='Create'][role='button']").last
    expect(create_button).not_to_be_visible()

    # ---------------------
    context.close()
    browser.close()

def test_52398():
    with sync_playwright() as playwright:
        run(playwright)
