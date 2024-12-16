import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
from playwright.sync_api import sync_playwright, expect, BrowserContext
from playwright._impl._browser import Browser
from playwright._impl._page import Page

# Import the trace cleaner
from utils.trace_cleaner import trace_cleaner

# Utility to generate a random email

def generate_random_email():
    return f"freelanceapptest+643895@gmail.com"

# Updated login_user to accept an existing context instead of creating a new browser.
# Returns (page, user_email) so that the main test can manage browser/context.

def login_user(context: BrowserContext, first_name="A", last_name="Khan") -> tuple[Page, str]:
    page = context.new_page()
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

    try:
        # Step 4: Select 'Track and budget expenses' in onboarding page and click Continue
        page.locator("text='Track and budget expenses'").click(timeout=2000)
        page.get_by_role("button", name="Continue").click()
        page.wait_for_timeout(1000)

        # Step 5: Enter first name, last name and click continue
        page.locator('input[name="fname"]').fill(first_name)
        page.locator('input[name="lname"]').fill(last_name)
        page.get_by_role("button", name="Continue").last.click()
        page.wait_for_timeout(1000)

        # Click the button with text 'Get Started'
        page.locator("text='Get Started'").click()
        page.wait_for_timeout(1000)

    except Exception:
        # Step 4 fallback: Enter first name, last name in settings
        page.get_by_label("My settings").click()
        page.get_by_text("Display name").click()
        page.get_by_role("textbox", name="First name").click()
        page.get_by_role("textbox", name="First name").fill(first_name)
        page.get_by_role("textbox", name="Last name").click()
        page.get_by_role("textbox", name="Last name").fill(last_name)
        page.get_by_role("button", name="Save").click()
        page.get_by_label("Inbox").click()

    return page, user_email

# Updated set_default_currency to accept just a page.
def set_default_currency(
    page: Page,
    search_text: str,
    currency: str,
) -> None:
    # Step 1: Open the 'Default currency' menu item
    default_currency_button = page.locator('div[role="menuitem"]').get_by_text("Default currency")
    expect(default_currency_button).to_be_visible()
    default_currency_button.click()

    # Step 2: Fill in the desired currency text and verify
    input_currency = page.locator('input[aria-label="Default currency"]')
    input_currency.fill(search_text)
    expect(page.get_by_test_id("WorkspaceProfileCurrencyPage")).to_contain_text(currency)

# Updated check_currency_in_workspace_chat to accept just a page.
def check_currency_in_workspace_chat(
    page: Page
) -> None:
    # Step 1: Click on the "+" icon to start a new workspace
    plus_icon = page.locator('button[aria-label="Start chat (Floating action)"]')
    expect(plus_icon).to_be_visible()
    plus_icon.click()

    # Step 2: Click on the "+" icon to start a new workspace and search "rupee" as default currency
    new_workspace_button = page.locator('div[aria-label="New workspace"]')
    expect(new_workspace_button).to_be_visible()
    new_workspace_button.click()

    set_default_currency(page, 'rupee', "INR - ₹")

# Main test that records a trace and cleans it, even if the test fails.

def test_currency_search():
    with sync_playwright() as p:
        trace_path = "/app/expensify/user_tool/output_browser1.zip"
        browser = None
        context = None
        try:
            # Create the browser and context
            browser = p.chromium.launch(headless=True, args=[
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process"
            ])
            context = browser.new_context()
            # Start Playwright tracing
            context.tracing.start(screenshots=True, snapshots=True)

            # Step 1: Log in the user and begin test actions
            page, user_email = login_user(context)

            # Step 2: Validate the currency selection
            check_currency_in_workspace_chat(page)

        except Exception as e:
            # Re-raise so test frameworks can see the failure
            raise e
        finally:
            # Stop tracing and clean the trace, ensuring it's saved even on failure
            if context:
                context.tracing.stop(path=trace_path)
                trace_cleaner(trace_path)
            if browser:
                browser.close()
