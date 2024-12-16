import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page

from utils.trace_cleaner import trace_cleaner

# Utility to generate a random email for testing
def generate_random_email():
    return "expensify624+1734042435@gmail.com"


def login_user(p: PlaywrightContextManager, first_name="A", last_name="Khan") -> tuple[Browser, Page, str]:
    # Launch Chromium browser and open a new page
    browser = p.chromium.launch(channel="chrome", headless=True, slow_mo=1000, args=[
        "--disable-web-security",
        "--disable-features=IsolateOrigins,site-per-process"
    ])
    page = browser.new_page()
    user_email = generate_random_email()

    # Step 1: Open the Expensify URL
    page.goto('https://dev.new.expensify.com:8082/') 

    # Step 2: Enter the generated email and click continue
    page.locator('input[type="email"]').fill(user_email)

    page.locator('button[tabindex="0"]').click()
    time.sleep(1)

    # Step 3: Click the join button if necessary (in case it didn't register the first time)
    try: 
        page.locator('button[tabindex="0"]').click() 
        time.sleep(1)
    except Exception:
        pass
    
    # Step 4: Ensure that the user has reached the main menu
    expect(page.locator("text=What do you want to do today?")).to_be_visible()
        
    # Step 5: Select 'Track and budget expenses' during onboarding and click Continue
    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()
    time.sleep(1)

    # Step 6: Enter first name and last name, then click continue
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()
    time.sleep(1)

    # Return the browser, page
    return browser, page


def test_removal_of_features():
    with sync_playwright() as p:
        # Step 1: Log in the user and begin test actions
        browser, page = login_user(p)
        context = page.context
        # Start tracing
        context.tracing.start(screenshots=True, snapshots=True, sources=True)

        try:
            # Step 1: Click on the Global create ("+") icon
            plus_icon = page.locator('button[aria-label="Start chat (Floating action)"]')
            expect(plus_icon).to_be_visible()
            plus_icon.click()
            
            # Step 2: Verify that Split Expense, Assign Tasks, Pay Someone options are not visible
            expect(page.locator('div[aria-label="Split expense"]')).not_to_be_visible()
            expect(page.locator('div[aria-label="Pay someone"]')).not_to_be_visible()
            expect(page.locator('div[aria-label="Assign task"]')).not_to_be_visible()
        except Exception as e:
            # Raise again to keep test failure visible
            raise e
        finally:
            # Stop tracing and export
            context.tracing.stop()
            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            context.tracing.export(path=trace_path)
            trace_cleaner(trace_path)
            # Step 3: Close the browser
            browser.close()
