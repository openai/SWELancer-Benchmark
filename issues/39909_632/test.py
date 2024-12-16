import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from time import time
from playwright.sync_api import sync_playwright, expect
from playwright._impl._page import Page
from playwright._impl._browser_context import BrowserContext

def generate_random_email():
    timestamp = int(time())
    return f"bobexpensifytest+{timestamp}@gmail.com"


def login_user(page: Page, user_email: str, first_name="Milan", last_name="T") -> Page:
    # Step 1: Open expensify url
    page.goto('https://dev.new.expensify.com:8082/') 
    

    # Step 2: Enter email and click continue
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(1000)

    # Step 3: Click join button
    try: 
        page.locator('button[tabindex="0"]').click() 
    except Exception:
        pass
    expect(page.locator("text=What do you want to do today?")).to_be_visible()
        
    # Step 4: Select 'Track and budget expenses' in onobarding page and click Continue
    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()

    # Step 5: Enter first name, last name and click continue
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()

    return page


def create_new_workspace(
    page: Page,  
) -> Page:
    # Step 1: Click on + icon and click on "New workspace"
    plus_icon = page.locator('button[aria-label="Start chat (Floating action)"]')
    plus_icon.click()

    new_workspace_button = page.locator('div[aria-label="New workspace"]')
    new_workspace_button.click()

    # Step 2: Click on Back arrow to go back 
    back_arrow_button = page.locator('button[aria-label="Back"]')
    back_arrow_button.click()

    return page


def test_fallback_avatar_background():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=[
                    "--disable-web-security",
                    "--disable-features=IsolateOrigins,site-per-process",]
                    )
        
        context = browser.new_context()
        page = context.new_page()

        bob_email = "blablabla+39909@example.com"
        user_email = "blablabla@example.com"

        # Login as Bob 
        page = login_user(page, bob_email, first_name='Bob')

        page = create_new_workspace(page)

        plus_icon = page.locator('button[aria-label="Start chat (Floating action)"]')
        plus_icon.click()

        submit_expense_button = page.locator('div[aria-label="Start chat"]')
        submit_expense_button.click()

        page.locator('input[aria-label="Name, email, or phone number"]').last.click()

        page.keyboard.type(user_email)

        user_button = page.locator(f'button[aria-label="{user_email}"] div').first
        
        # Get the 'style' attribute of the button
        style_attribute = user_button.get_attribute("style")

        # Check if 'background-color: rgb(230, 225, 218)' is in the style attribute
        assert "background-color: rgb(230, 225, 218)" in style_attribute 

