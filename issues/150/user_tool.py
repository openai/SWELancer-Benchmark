import re
from playwright.sync_api import Playwright, sync_playwright, expect
import time
from utils.trace_cleaner import trace_cleaner

def get_mail_addr():
    timestamp = int(time.time())
    return f"aliceoglualicee+{timestamp}@gmail.com"

def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False, args=[
        '--ignore-certificate-errors',
        '--disable-web-security',
        '--disable-features=IsolateOrigins,site-per-process',
    ])
    context = browser.new_context(ignore_https_errors=True)
    # Start tracing
    context.tracing.start(screenshots=True, snapshots=True, sources=True)
    page = context.new_page()
    try:
        page.goto("https://dev.new.expensify.com:8082/")
        
        # Step 1: Log in
        user_mail = "aliceoglualicee+1739544967@gmail.com"
        page.get_by_test_id("username").click()
        page.get_by_test_id("username").fill(user_mail)
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
        page.get_by_label("New workspace").nth(1).click()
        page.wait_for_timeout(1000)
        
        # Step 4: Enable workflow
        page.get_by_text("More features").click()
        page.get_by_label("Configure how spend is").click()
        page.get_by_test_id("WorkspaceInitialPage").get_by_text("Workflows").click()
        page.wait_for_timeout(1000)
        
        # Step 5: Click connect bank account
        page.get_by_text("Connect bank account").click()
        page.wait_for_timeout(1000)
        
        # Step 6: Verify the app is not crashed
        locator = page.locator('div[dir="auto"]', has_text="Uh-oh, something went wrong!")
        expect(locator).not_to_be_visible()
    finally:
        # Stop tracing, export trace file and clean it
        context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
        trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
        context.close()
        browser.close()

def test_51961():
    with sync_playwright() as playwright:
        run(playwright)