"""
This is a simple test of whether the pay button changes to the review button after removing the category from the submitted expense.
"""
import time
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page


# Utility to generate a random email for testing
def generate_random_email():
    timestamp = int(time.time())
    return f'sunil.test.expensify+1740123732@gmail.com'

def login_user(p: PlaywrightContextManager, first_name="Sunil", last_name="G") -> tuple[Browser, Page, str]:
    # Launch Chromium browser and open a new page
    browser = p.chromium.launch(headless=False, args=["--disable-web-security",
"--disable-features=IsolateOrigins,site-per-process"
],slow_mo=4000)
    page = browser.new_page()
    user_email = generate_random_email()

    # Step 1: Open the Expensify URL
    page.goto('https://dev.new.expensify.com:8082/') 

    # Step 2: Enter the generated email and click continue
    page.locator('input[type="email"]').fill(user_email)
    page.get_by_role("button", name="Continue").click()
    
    

    # Step 3: Click the join button if necessary (in case it didn't register the first time)
    try: 
        page.get_by_role("button", name="Join").click() 
        
    except Exception:
        pass
    
    # Step 4: Ensure that the user has reached the main menu
    expect(page.locator("text=What do you want to do today?")).to_be_visible()
        
    # Step 5: Select 'Track and budget expenses' during onboarding and click Continue
    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()
    

    # Step 6: Enter first name and last name, then click continue
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()
    

    # Return the browser, page
    return browser, page

def test_Pay_Review_button():
     with sync_playwright() as p:
        # Log in the user and begin test actions
        browser, page = login_user(p)
        # Navigate to Start chat (Floating action)
        page.get_by_label("Start chat (Floating action)").click()
        # create New workspace
        page.get_by_text("New workspace").click()
        page.get_by_role("button", name="Confirm").click()
        # Navigate to the categories
        page.get_by_text("Categories").click()
        # Change the settings for categories
        page.get_by_test_id("WorkspaceCategoriesPage").get_by_role("button", name="Settings").click()
        page.get_by_label("Members must categorize all").click()
        # Back to the worspace page
        page.get_by_test_id("WorkspaceCategoriesSettingsPage").get_by_label("Back").click()
        # Go the newly created workspace
        page.get_by_test_id("WorkspaceInitialPage").get_by_label("Sunil G's Workspace").get_by_text("Sunil G's Workspace").click()
        # To submit new expense
        page.locator("div:nth-child(4) > div:nth-child(2) > div:nth-child(2) > div > div > div > div > div > div > div > div > div:nth-child(2) > div > div:nth-child(3) > div > div:nth-child(2) > div > div > div > div:nth-child(4) > div").click()
        page.get_by_text("Create expense").click()
        # To submit manual expense
        page.get_by_label("Manual").click()

        page.get_by_placeholder("0").click()

        page.get_by_placeholder("0").fill("100")

        page.locator("#numPadContainerView").get_by_role("button", name="Next").click()
        # Fill the merchant

        page.get_by_text("Merchant").click()

        page.get_by_role("textbox", name="Merchant").fill("abcde")
        page.get_by_role("button", name="Save").click()
        # To select the category
        page.get_by_text("Category").click()
        page.get_by_label("Advertising").click()
        # Submit the expense
        page.get_by_role("button", name="Create ₹100.00 expense").click()
        page.locator("div:nth-child(4) > div:nth-child(2) > div:nth-child(2) > div > div > div > div > div > div > div > div > div:nth-child(2) > div > div:nth-child(3) > div > div:nth-child(2) > div > div > div > div:nth-child(4) > div").click()
        # To submit 2nd expense
        page.get_by_text("Create expense").click()
        page.get_by_placeholder("0").fill("200")
        page.locator("#numPadContainerView").get_by_role("button", name="Next").click()
        # Fill the merchant
        page.get_by_text("Merchant").click()
        page.get_by_role("textbox", name="Merchant").fill("eghik")
        page.get_by_role("button", name="Save").click()
        # To select the category
        page.get_by_text("Category").click()
        page.get_by_label("Car").click()
        page.get_by_role("button", name="Create ₹200.00 expense").click()
        page.get_by_label("Reports").click()
        page.get_by_role("button", name="Outstanding").click()

        # To make edits in category field.
        page.wait_for_timeout(2000)
        page.get_by_role("button", name="View").nth(1).click()
        page.wait_for_timeout(2000)
        page.get_by_text("CategoryAdvertising").click()
        
        page.get_by_test_id("IOURequestStepCategory").get_by_label("Advertising").click()
        page.get_by_label("Back").click()
        # To check whether Pay button is visible or not initially
        button= page.locator("button").filter(has_text="Review").nth(0)
        expect(button).to_be_visible()

        # Close the browser after completing the test
        browser.close()
