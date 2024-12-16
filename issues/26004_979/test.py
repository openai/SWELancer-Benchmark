import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page

# Utility to generate a random email
def generate_random_email():
    task_number = 26004
    return f"jellystarfish+{task_number}@gmail.com"


def login_user(p: PlaywrightContextManager, first_name="Milan", last_name="T") -> tuple[Browser, Page, str]:
    # Launch Chromium and open a new page
    browser = p.chromium.launch(headless=True, args=["--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"])
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    user_email = generate_random_email()

    # Step 1: Open expensify url
    page.goto('https://dev.new.expensify.com:8082/') 

    # Step 2: Enter email and click continue
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(2000)

    # Step 3: Click join button
    try: 
        page.locator('button[tabindex="0"]').click()
        page.wait_for_timeout(2000)
    except Exception:
        pass

    if page.locator("text=What do you want to do today?").is_visible():
        # Step 4: Select 'Track and budget expenses' on onboarding page and click Continue
        page.locator("text='Track and budget expenses'").click()
        page.get_by_role("button", name="Continue").click()

        # Step 5: Enter first name, last name and click continue
        page.locator('input[name="fname"]').fill(first_name)
        page.locator('input[name="lname"]').fill(last_name)
        page.get_by_role("button", name="Continue").last.click()
        page.wait_for_timeout(2000)

    return browser, page, context, user_email


def test_iou_subtitle_offline():
    with sync_playwright() as p:
        # Step 1: Login the user and set up the page
        browser, page, context, user_email = login_user(p)

        # Step 2: Go offline.
        context.set_offline(True)
        page.wait_for_timeout(2000)

        # Step 3: Submit an expense to a new user (i.e., someone you have never chatted with).
        page.get_by_label("Start chat (Floating action)").click()
        page.get_by_text("Submit expense").click()
        page.get_by_label("Manual").click()
        page.get_by_placeholder("0").fill("100")
        page.locator("#numPadContainerView").get_by_role("button", name="Next").click()
        page.get_by_test_id("selection-list-text-input").fill("testuser@gmail.com")
        page.get_by_label("testuser@gmail.com").click()
        
        save_button = page.locator('button[data-listener="Enter"]', has_text="Submit")
        save_button.click()
        page.wait_for_timeout(1000)

        # Step 4: Open the IOU card and assert that subtitle with user email is visible
        page.get_by_label("View details").click()
        # Expect that the subtitle "From testuser@gmail.com" is visible
        expect(page.get_by_label("From testuser@gmail.com")).to_be_visible()
        # Clicking on the subtitle leads you back to the chat
        page.get_by_label("From testuser@gmail.com").click()
        expect(page.get_by_text("This is the beginning of your chat with testuser@gmail.com.")).to_be_visible()

        # ---------------------
        context.close()
        browser.close()

