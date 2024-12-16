import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page


# Utility function to generate a random email using the current timestamp
def generate_random_email():
    task_number = 28265
    return f"checkissue+{task_number}@gmail.com"


# Function to log in the user and complete the initial onboarding process
def login_user(p: PlaywrightContextManager, first_name="Milan", last_name="T") -> tuple[Browser, Page, str]:
    # Launch Chromium browser and create a new page
    browser = p.chromium.launch(headless=True, args=["--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"],
    proxy={"server": "http://localhost:8080"},
    slow_mo=500)
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    user_email = generate_random_email()

    # Step 1: Open Expensify's dev environment
    page.goto('https://dev.new.expensify.com:8082/') 

    # Step 2: Enter the generated email and proceed to the next step
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(2000)

    # Step 3: Click the "Join" button if it's present
    try: 
        page.locator('button[tabindex="0"]').click()
        page.wait_for_timeout(2000)
    except Exception:
        pass

    # Assert that the user has reached the onboarding page
    expect(page.locator("text=What do you want to do today?")).to_be_visible()
        
    # Step 4: Select 'Track and budget expenses' and proceed
    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()

    # Step 5: Enter the first and last name, then proceed
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()
    page.wait_for_timeout(2000)

    return browser, page, context, user_email


# Test to verify that Spanish emoji text is correctly converted to an emoji after changing language
def test_spanish_emoji_text():
    with sync_playwright() as p:
        # Step 1: Log in the user and complete the onboarding process
        browser, page, context, user_email = login_user(p)
        page.wait_for_timeout(1000)

        # Step 2: Open a chat or report and focus on the composer
        # page.locator("div:nth-child(3) > div:nth-child(2) > div > div > div > div > div").first.click()
        page.locator('span:text("Milan T (you)")').click()
        page.wait_for_timeout(1000)
        page.get_by_role("textbox").click()
        page.wait_for_timeout(1000)

        # Step 3: Enter Spanish emoji text (e.g., ":rosa:" for rose emoji) into the composer
        page.get_by_role("textbox").fill("Hi :rosa:")
        page.wait_for_timeout(1000)

        # Step 4: Navigate to user settings and change the language to Spanish
        page.get_by_label("My settings").click()
        page.wait_for_timeout(1000)
        page.get_by_text("Preferences").click()
        page.wait_for_timeout(1000)
        page.get_by_text("Language").click()
        page.wait_for_timeout(1000)
        page.get_by_label("Spanish").click()
        page.wait_for_timeout(1000)

        # Step 5: Return to the same report and verify the emoji is displayed correctly
        page.get_by_label("Recibidos").click()
        page.wait_for_timeout(2000)

        # Expect that the text has been converted into the corresponding rose emoji ("🌹")
        expect(page.get_by_text("🌹", exact=True)).to_be_visible()
       
        browser.close()

