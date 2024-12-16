import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import re
from playwright.sync_api import sync_playwright
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page

# Utility to generate email
def generate_email():
    timestamp = '1278784'
    return f"turingtemp+{timestamp}@gmail.com"


def login_user(p: PlaywrightContextManager, first_name="Ayush", last_name="G") -> tuple[Browser, Page, str]:
    # Launch chromiun and open new page
    browser = p.chromium.launch(
            channel="chrome",
            headless=True,
            args=[
                "--ignore-certificate-errors",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process"
            ],
            proxy={"server": "http://localhost:8080"},
            slow_mo=1000
        )
    page = browser.new_page()
    user_email = generate_email()

    # Step 1: Open expensify url
    page.goto('https://dev.new.expensify.com:8082/') 

    # Step 2: Enter email and click continue
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()

    # Step 3: Click join button
    try: 
        page.locator('button[tabindex="0"]').click() 
        page.wait_for_timeout(3000)
    except Exception:
        pass
    try: 
        page.locator('button[tabindex="0"]').click() 
        page.wait_for_timeout(3000)
    except Exception:
        pass
        
    # Step 4: Select 'Track and budget expenses' in onobarding page and click Continue
    page.locator("text='Track and budget expenses'").click()
    
    # Step 5: Enter first name, last name and click continue
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()
    
    return browser, page, user_email


def submit_expense_in_workspace_chat(
    browser: Browser, 
    page: Page, 
    user_email: str, 
    amount: str = "1000"
) -> tuple[Browser, Page, str]:
    # Step 1: Click on workspace chat
    workspace_chat = page.locator('button[aria-label="Navigates to a chat"]', has_text="Ayush G's Workspace").first
    workspace_chat.click()
    
    # Step 2: Click on "+" icon and click submit expense
    plus_create_icon = page.locator('button[aria-label="Create"]').last
    plus_create_icon.click()
    
    submit_expense_button = page.locator('div[aria-label="Submit expense"]')
    submit_expense_button.click()
    
    # Step 3: Click on "Manual" button and enter amount
    manual_button = page.locator('button[aria-label="Manual"]')
    manual_button.click()
    
    page.locator('input[role="presentation"]').fill(amount)

    # Step 4: Click on Next button
    next_button = page.locator('button[data-listener="Enter"]', has_text="Next").first
    next_button.click()
    
    # Step 5: Add merchant details
    merchant_field = page.locator('div[role="menuitem"]', has_text="Merchant")
    merchant_field.click()
    
    page.locator('input[aria-label="Merchant"]').fill("https://staging.new.expensify.com/r/575354256634947/165034783536884819")

    save_button = page.locator('button', has_text="Save")
    save_button.click()
    
    # Step 6: Submit the expense
    save_button = page.locator('button[data-listener="Enter"]', has_text="Submit")
    save_button.click()
    
    return browser, page, user_email


def test_save_description_in_submitted_expense():
    with sync_playwright() as p:
        # Step 1: Login user 
        browser, page, user_email = login_user(p)

        # Step 2: Click on + icon and click on "New workspace"
        plus_icon = page.locator('button[aria-label="Start chat (Floating action)"]')
        plus_icon.click()
        
        new_workspace_button = page.locator('div[aria-label="New workspace"]')
        new_workspace_button.click()
        
        # Step 3: Click on Back arrow to go back and navigate to inbox screen
        back_arrow_button = page.locator('button[aria-label="Back"]')
        back_arrow_button.click()

        inbox_menu = page.locator('button[aria-label="Inbox"]')
        inbox_menu.click()
        
        # Step 4: Submit an expense
        browser, page, user_email = submit_expense_in_workspace_chat(browser, page, user_email)

        page.wait_for_timeout(3000)
        page.get_by_role("button", name=re.compile(r'Pay .+ elsewhere')).click()
        page.get_by_label("View details").first.click()

        page.set_viewport_size({'width': 375, 'height': 812}) 
        page.wait_for_timeout(3000)

        container = page.locator('div[aria-label="https://staging.new.expensify.com/r/575354256634947/165034783536884819"]')

        # Locate the nested div containing the long text inside the container
        text_div = container.locator('div:text("https://staging.new.expensify.com/r/575354256634947/165034783536884819")')

        # Get clientWidth and scrollWidth of the text div
        client_width = text_div.evaluate("el => el.clientWidth")
        scroll_width = text_div.evaluate("el => el.scrollWidth")

        assert client_width == scroll_width
        
        browser.close()

