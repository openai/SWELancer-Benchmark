import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page

from utils.trace_cleaner import trace_cleaner

EMAIL = "freelancer.test.exp@gmail.com"
EMAIL_PREFIX = EMAIL.split('@')[0]

def generate_random_email():
    timestamp = int(time.time())
    return f"{EMAIL_PREFIX}+{timestamp}@gmail.com"

def login_user(p: PlaywrightContextManager, first_name="A", last_name="Khan") -> tuple[Browser, Page, str]:
    # Launch Chromium browser and open a new page
    browser = p.chromium.launch(headless=True, args=[
            "--ignore-certificate-errors",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ])
    page = browser.new_page()
    context = browser.new_context()
    user_email = generate_random_email()

    # Open the Expensify URL
    page.goto('https://dev.new.expensify.com:8082/') 

    # Enter the generated email and click continue
    page.get_by_test_id("username").fill(generate_random_email())
    page.wait_for_timeout(1000)
    page.get_by_role("button", name="Continue").click()
    page.wait_for_timeout(1000)
    page.get_by_role("button", name="Join").click()

    try:
        expect(page.locator("text=What do you want to do today?")).to_be_visible()
        page.get_by_text("Track and budget expenses").click()
        page.get_by_role("button", name="Continue").click()
        page.get_by_role("textbox", name="First name").fill(first_name)
        page.get_by_role("textbox", name="Last name").fill(last_name)
        page.wait_for_timeout(1000)
        page.get_by_role("button", name="Continue").click()
    except:
        pass
    
    return browser, page, context

def test_exit_survey_confirmation_page():
    with sync_playwright() as p:
        browser, page, context = login_user(p)
        trace_path = "/app/expensify/user_tool/output_browser1.zip"

        # Start tracing
        context.tracing.start(screenshots=True, snapshots=True)

        try:
            # Navigate to exit-survey reason page
            page.goto('https://dev.new.expensify.com:8082/settings/exit-survey/reason ')
            time.sleep(1)
            # Check one of the box
            page.get_by_text("I don't understand how to use New Expensify.").click()
            # Click on next button
            page.get_by_text("Next").click()
            # Fill in the textbox
            page.get_by_role("textbox", name="Your response").fill("N/A")
            # Click on next button
            page.get_by_role("button", name="Next").click()
            # Click on Switch to Expensify Classic button
            page.get_by_role("button", name="Switch to Expensify Classic").click()
            # Wait for the ExitSurveyConfirmPage modal to disappear
            time.sleep(1)     
            # Verify the modal is not visible  
            expect(page.get_by_test_id("ExitSurveyConfirmPage")).not_to_be_visible()
        except Exception as e:
            # Reraise the exception after we do our cleanup
            raise e
        finally:
            # Stop tracing
            context.tracing.stop()
            # Export trace
            context.tracing.export(path=trace_path)
            # Clean trace
            trace_cleaner(trace_path)
            # Close the browser
            browser.close()
