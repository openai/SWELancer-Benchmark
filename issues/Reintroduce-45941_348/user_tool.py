import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from utils.trace_cleaner import trace_cleaner

# Utility to generate a random email for testing
def generate_random_email():
    timestamp = 122100012342
    return f"usama.shahid1255198+{timestamp}@gmail.com"


def login_user(p: PlaywrightContextManager, first_name="A", last_name="Khan"):
    # Launch chromium browser and open a new page
    browser = p.chromium.launch(headless=True, slow_mo=1000, args=[
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
        ])
    context = browser.new_context()
    page = context.new_page()
    user_email = generate_random_email()

    # Step 1: Open the Expensify URL
    page.goto('https://dev.new.expensify.com:8082/') 

    # Step 2: Enter the generated email and click continue
    page.get_by_test_id("username").fill(user_email)
    page.get_by_role("button", name="Continue").click()
    page.get_by_role("button", name="Join").click()

    page.get_by_role("button", name="Join").wait_for(state="hidden")

    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()

    page.locator('input[name="fname"]').fill("first_name")
    page.locator('input[name="lname"]').fill("last_name")
    page.get_by_role("button", name="Continue").last.click()

    # Return the browser, page
    return browser, page, context


def test_old_dot_page_redirection():
    with sync_playwright() as p:
        browser, page, context = login_user(p)

        # Start recording the trace
        context.tracing.start(screenshots=True, snapshots=True, sources=True)

        try:
            # Navigate to exit-survey reason page
            page.goto('https://dev.new.expensify.com:8082/settings/exit-survey/reason') 

            # Check one of the boxes and fill in the form
            page.get_by_text("I don't understand how to use New Expensify.").click()

            # Click on the next button and proceed
            page.get_by_text("Next").click()

            # Fill in the response textbox
            page.get_by_role("textbox", name="Your response").fill("N/A")

            # Click on the Next button
            page.get_by_role("button", name="Next").click()

            # Wrap the click action inside expect_page to listen for the new tab
            with context.expect_page() as new_page_info:
                page.get_by_role("button", name="Switch to Expensify Classic").click()
                page.wait_for_timeout(1000)

            new_page = new_page_info.value

            # Assert that the new page was successfully opened
            assert new_page is not None, "A new tab should have opened but it didn't."
            print("New tab was successfully opened.")

        except PlaywrightTimeoutError:
            assert False, "Failed to open new tab after clicking the 'Switch to Expensify Classic' button."

        finally:
            # Stop recording the trace and save it
            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            # Clean the trace
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")

            # Close the browser
            browser.close()
