import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page


# Utility to generate a random email
def generate_random_email():
    return f"freelanceapptest+643895@gmail.com"


def login_user(p: PlaywrightContextManager, first_name="A", last_name="Khan") -> tuple[Browser, Page, str]:
    # Launch Chromium browser and open a new page
    browser = p.chromium.launch(headless=True, args=[
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
    page.wait_for_timeout(1000)

    # Step 3: Click the join button if necessary (in case it didn't register the first time)
    try: 
        page.locator('button[tabindex="0"]').click() 
        page.wait_for_timeout(1000)
    except Exception:
        pass
    
    
    # Step 4: Select 'Track and budget expenses' in onboarding page and click Continue
    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()
    page.wait_for_timeout(1000)

    # Step 5: Enter first name, last name and click continue
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()
    page.wait_for_timeout(1000)

    # Return the browser, page
    return browser, page

def set_default_currency(
    browser: Browser, 
    page: Page,
    search_text: str,
    currency: str,
) -> tuple[Browser, Page]:
    # Step 1: Open the 'Default currency' menu item
    default_currency_button = page.locator('div[role="menuitem"]').get_by_text("Default currency")
    expect(default_currency_button).to_be_visible()
    default_currency_button.click()
    
    # Step 2: Fill in the desired currency text and verify if the search matches
    input_currency = page.locator('input[aria-label="Default currency"]')
    input_currency.fill(search_text)
    expect(page.get_by_test_id("WorkspaceProfileCurrencyPage")).to_contain_text(currency)
    
    # Return the browser and page for further steps
    return browser, page


def check_currency_in_workspace_chat(
    browser: Browser, 
    page: Page, 
) -> tuple[Browser, Page]:
    
    # Step 1: Click on the "+" icon to start a new workspace 
    plus_icon = page.locator('button[aria-label="Start chat (Floating action)"]')
    expect(plus_icon).to_be_visible()
    plus_icon.click()

    # Step 2: Click on the "+" icon to start a new workspace and search "rupee" as default currency
    new_workspace_button = page.locator('div[aria-label="New workspace"]')
    expect(new_workspace_button).to_be_visible()
    new_workspace_button.click()
    
    browser, page = set_default_currency(browser, page, 'rupee', "INR - ₹")

    return browser, page


def test_currency_search():
    with sync_playwright() as p:
        # Step 1: Log in the user and begin test actions
        browser, page = login_user(p)

        # Step 2: Validate the currency selection
        browser, page = check_currency_in_workspace_chat(browser, page)

        # Step 3: Close the browser after completing the test
        browser.close()

