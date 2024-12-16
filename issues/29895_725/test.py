import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page


# Utility to generate a random email for testing
def login_user(p: PlaywrightContextManager, first_name="A", last_name="Khan") -> tuple[Browser, Page, str]:
    # Launch Chromium browser and open a new page
    browser = p.chromium.launch(headless=True, args=["--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"],
    proxy={"server": "http://localhost:8080"})
    page = browser.new_page()
    user_email = "checkissue+29895@gmail.com"

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
    page.wait_for_timeout(5000)
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
    page.wait_for_timeout(1000)

    # Return the browser, page
    return browser, page

def test_duplicate_waypoints():
    with sync_playwright() as p:
        # Log in the user and begin test actions
        browser, page = login_user(p)
        # Navigate the user is in their own personal space
        page.get_by_text("A Khan (you)").click()
        page.wait_for_timeout(1000)
        # Click on the '+' (Create) icon
        page.get_by_role("button", name="Create").click()
        page.wait_for_timeout(1000)
        # Click on 'Track expense'
        page.get_by_label("Track expense").click()
        # Select 'Distance' from RHS modal
        page.get_by_role("button", name="Distance").click()
        page.wait_for_timeout(1000)
        # Click on 'Start' from RHS modal
        page.get_by_test_id("IOURequestStartPage").get_by_role("button", name="Start").click()
        page.wait_for_timeout(1000)
        # Type in the 'Start' location
        page.locator('input[class="css-textinput-11aywtz r-placeholderTextColor-6taxm2"]').fill("India Gate")
        page.wait_for_timeout(1000)
        # Select the location from the drop down list
        page.get_by_text("New Delhi, Delhi, India", exact=True).click()
        page.wait_for_timeout(1000)
        # Click on 'Stop' from RHS modal
        page.get_by_test_id("IOURequestStartPage").get_by_role("button", name="Stop").click()
        page.wait_for_timeout(1000)
        # Type in the 'Stop' location
        page.locator('input[class="css-textinput-11aywtz r-placeholderTextColor-6taxm2"]').fill("India Gate")
        page.wait_for_timeout(1000)
        # Select the location from the drop down list
        page.get_by_text("New Delhi, Delhi, India", exact=True).click()
        page.wait_for_timeout(1000)
        # Verify the 'Add Stop' button is visible
        expect(page.get_by_role("button", name="Add stop")).to_be_visible()
        page.wait_for_timeout(1000)
        # Click on 'Add Stop' 
        page.get_by_role("button", name="Add stop").click()
        page.wait_for_timeout(1000)
        # Type in the 'Stop' location
        page.locator('input[class="css-textinput-11aywtz r-placeholderTextColor-6taxm2"]').fill("India Gate")
        page.wait_for_timeout(1000)
        # Select the location from the drop down list
        page.get_by_text("New Delhi, Delhi, India", exact=True).click()
        page.wait_for_timeout(1000)
        # Click on the Next button
        page.get_by_role("button", name="Next").nth(1).click()
        page.wait_for_timeout(1000)
        # Verify the Track expense button is not visible
        expect(page.get_by_role('button', name="Track expense")).not_to_be_visible()
        page.wait_for_timeout(1000)
        # Close the browser after completing the test
        browser.close()

