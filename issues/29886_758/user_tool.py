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
    return f"freelanceapptest+6787475@gmail.com"


def login_user(p: PlaywrightContextManager, first_name="A", last_name="Khan") -> tuple[Browser, Page, str]:
    # Launch Chromium browser and open a new page
    browser = p.chromium.launch(
        channel="chrome",
        headless=True,
        args=[
            "--ignore-certificate-errors",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ],
        proxy={"server": "http://localhost:8080"},
        slow_mo=500
    )

    page = browser.new_page()
    user_email = generate_random_email()

    # Step 1: Open the Expensify URL
    page.goto('https://dev.new.expensify.com:8082/')

    # Step 2: Enter the generated email and click continue
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(1000)

    # Step 3: Click the join button if necessary (in case it didn't register the first time)
    try:
        page.locator('button[tabindex="0"]').click()
        page.wait_for_timeout(1000)
    except Exception:
        pass
    
    # Step 4: Ensure that the user has reached the main menu
    expect(page.locator("text=What do you want to do today?")).to_be_visible()
        
    # Step 5: Select 'Track and budget expenses' during onboarding and click Continue
    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()
    page.wait_for_timeout(1000)

    # Step 6: Enter first name and last name, then click continue
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()
    page.wait_for_timeout(2000)

    # Return the browser, page
    return browser, page, user_email


def test_add_stop_button():
    with sync_playwright() as p:
        # Log in the user
        browser, page, _ = login_user(p)
        context = page.context

        # Start tracing
        context.tracing.start(
            screenshots=True,
            snapshots=True,
            sources=True
        )

        try:
            # Test actions
            page.get_by_text("A Khan (you)").click()
            page.get_by_role("button", name="Create").click()
            page.get_by_label("Track expense").click()
            page.get_by_role("button", name="Distance").click()
            expect(page.get_by_role("button", name="Add stop")).not_to_be_visible()
            page.get_by_test_id("IOURequestStartPage").get_by_role("button", name="Start").click()
            page.locator('input[class="css-textinput-11aywtz r-placeholderTextColor-6taxm2"]').fill("West Pine Street")
            page.get_by_text("Louisville, CO, USA ").click()
            expect(page.get_by_role("button", name="Add stop")).not_to_be_visible()
            page.get_by_test_id("IOURequestStartPage").get_by_role("button", name="Stop").click()
            page.locator('input[class="css-textinput-11aywtz r-placeholderTextColor-6taxm2"]').fill("East Pine Street")
            page.get_by_text("Nederland, CO, USA").click()
            expect(page.get_by_role("button", name="Add stop")).to_be_visible()
        except Exception:
            # Reraise any test failure after we do the trace cleanup in the finally block
            raise
        finally:
            # Stop tracing and clean the trace
            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            context.tracing.stop(path=trace_path)
            trace_cleaner(trace_path)
            # Close the browser
            browser.close()
