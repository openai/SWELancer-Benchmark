import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._page import Page

from utils.trace_cleaner import trace_cleaner  # Added import for trace_cleaner

# Utility to generate a random email
def generate_random_email():
    timestamp = int(time.time())
    return f"kenworktestemail+960@gmail.com"

# Updated login_user to accept an existing context, rather than creating one
# Returns (page, user_email)
def login_user(context: PlaywrightContextManager, first_name="Milan", last_name="T") -> tuple[Page, str]:
    page = context.new_page()
    user_email = generate_random_email()

    # Step 1: Open the Expensify URL
    page.goto('https://dev.new.expensify.com:8082/')

    # Step 2: Enter a generated email and click continue
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(1000)

    # Step 3: Click the join button if available, otherwise skip
    try:
        page.locator('button[tabindex="0"]').click()
        page.wait_for_timeout(1000)
    except Exception:
        pass

    # Step 4: Ensure that the user reaches the dashboard by checking for visible text
    expect(page.locator("text=What do you want to do today?")).to_be_visible()

    # Step 5: Select 'Track and budget expenses' in the onboarding page and click Continue
    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()
    page.wait_for_timeout(1000)

    # Step 6: Enter first name, last name, and continue
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()
    page.wait_for_timeout(1000)

    return page, user_email


def test_choose_file_name():
    with sync_playwright() as p:
        trace_path = "/app/expensify/user_tool/output_browser1.zip"
        browser = None
        context = None
        page = None
        try:
            # Create browser and context, start tracing
            browser = p.chromium.launch(headless=True, args=["--disable-web-security", "--disable-features=IsolateOrigins, site-per-process"])
            context = browser.new_context(ignore_https_errors=True)
            context.tracing.start(screenshots=True, snapshots=True, sources=True)

            # Step 1: Login user (via the updated login_user function)
            page, user_email = login_user(context)

            # Rest of test
            page.get_by_label("Start chat (Floating action)").click()
            page.get_by_text("Submit expense").click()
            page.wait_for_timeout(2000)

            # Explicitly checking if the text "Choose file" is visible
            expect(page.get_by_text("Choose file", exact=True)).to_be_visible()

        except Exception as e:
            # Raise the error so test frameworks can handle it
            raise e
        finally:
            # Stop tracing and clean the trace, then close browser
            if context:
                context.tracing.stop(path=trace_path)
                trace_cleaner(trace_path)
            if browser:
                browser.close()
