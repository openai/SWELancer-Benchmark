import time
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page

# Utility function to generate a unique random email for testing
def generate_random_email():
    return "t1533148+1740172175@gmail.com"


# Function to log in a user and complete onboarding steps
def login_user(p: PlaywrightContextManager, first_name="Milan", last_name="T") -> tuple[Browser, Page, str]:
    # Launch Chromium browser in visible mode (non-headless)
    browser = p.chromium.launch(headless=False, args=[
        "--ignore-certificate-errors",
        "--disable-web-security",
        "--disable-features=IsolateOrigins,site-per-process"
    ],
    proxy={"server": "http://localhost:8080"}, slow_mo=1000)
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    user_email = generate_random_email()

    # Step 1: Open the Expensify URL
    page.goto('https://dev.new.expensify.com:8082')

    # Step 2: Enter the generated email and click continue
    page.locator('input[type="email"]').fill(user_email)
    page.get_by_role("button", name="Continue").click()
    try:
        try:
            page.wait_for_selector('button[tabindex="0"]:has-text("Join")', timeout=15000) 
            page.get_by_role("button", name="Join").click()
            page.locator("text='Track and budget expenses'").click()
            page.locator("body").press("Enter")
            page.wait_for_timeout(1000)
            # Enter first name and last name
            page.locator('input[name="fname"]').fill(first_name)
            page.locator('input[name="lname"]').fill(last_name)
            page.get_by_role("button", name="Continue").last.click()
            page.wait_for_timeout(4000) 
        except:
            page.get_by_test_id("SignInPage").get_by_test_id("validateCode").fill("123456")
    except:
        pass

    return browser, context, page, user_email

# Test to verify opening distance receipt from another workspace opens without issue
def test_open_receipt_different_workspace():
    with sync_playwright() as p:
        browser, context, page, user_email1 = login_user(p)
        page.get_by_label("My settings").click()
        page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()
        page.get_by_label("New workspace").first.click()
        page.get_by_label("Back").click()
        page.get_by_label("Inbox").click()
        page.locator('button[aria-label="Navigates to a chat"]', has_text="Milan T's Workspace").last.click()
        page.get_by_label("Create").last.click()
        page.wait_for_timeout(3000)
        try:
            page.get_by_label("Create expense").click()
        except:
            page.get_by_label("Submit expense").click()
        page.get_by_label("Manual").click()
        page.get_by_placeholder("0").fill("100")
        page.locator("#numPadContainerView").get_by_role("button", name="Next").click()
        page.get_by_role("menuitem", name="Merchant Required").click()
        page.get_by_role("textbox", name="Merchant").fill("test")
        page.get_by_role("button", name="Save").click()
        page.get_by_role("button", name="Submit ₹").click()
        page.get_by_label("View details").click(button="right")
        page.get_by_label("Hold").click()
        page.get_by_role("textbox", name="Reason").fill("test")
        page.get_by_role("button", name="Hold expense").click()
        page.get_by_label("View details").click()
        expect(page.get_by_text("This request is onholdHold is")).to_be_visible()
        page.get_by_text("This request is onholdHold is").click()
        expect(page.get_by_role("button", name="Got it")).to_be_visible()
        context.close()
        browser.close()