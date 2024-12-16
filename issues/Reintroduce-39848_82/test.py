import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import re
from playwright._impl._page import Page
from playwright.sync_api import sync_playwright, expect, Playwright

first_name = "Alice"
last_name = "Aliceoglu"

def login_user(page: Page) -> None:
    # Step 1: Enter email and click continue
    username_input = page.get_by_test_id("username")
    username_input.click()
    username_input.fill("rgulraiz2000+7697208@gmail.com")
    continue_button = page.get_by_role("button", name="Continue")
    continue_button.click()
    page.wait_for_timeout(2000)
    
    # Step 2: Click join button
    join_button = page.get_by_role("button", name="Join")
    join_button.click()
    page.wait_for_timeout(2000)
    
     # Step 3: Select 'Track and budget expenses' in onboarding page and click Continue
    track_expenses_text = page.get_by_text("Track and budget expenses")
    track_expenses_text.click()
    page.wait_for_timeout(1000)


def enter_user_information(page:Page) -> None:
    # Step 1: Enter first name, last name and click continue
    first_name_input = page.get_by_role("textbox", name="First name")
    first_name_input.fill(first_name)
    first_name_input.press("Tab")
    last_name_input = page.get_by_role("textbox", name="Last name")
    last_name_input.fill(last_name)
    
    
    # Step 2: Click continue button
    continue_button_after_names = page.get_by_role("button", name="Continue")
    continue_button_after_names.click()
    page.wait_for_timeout(1000)

def reproduce_scenario(page: Page) -> None:
    # Step 1: Open setting page
    settings_button = page.get_by_label("My settings")
    settings_button.click()
    page.wait_for_timeout(1000)
    
    # Step 2: Click status button
    status_element = page.locator('div[dir="auto"]', has_text="Status")
    status_element.click()

    # Step 3: Add status message
    page.get_by_label("statusText").fill("test message")
    status_save_button = page.get_by_role("button", name="Save")
    status_save_button.click()
    page.wait_for_timeout(1000)
    
    # Step 5: Open status message
    status_message = page.locator("div").filter(has_text=re.compile(r"^💬 test message$")).first
    status_message.click()
    page.wait_for_timeout(2000)

    # Click clear status button
    clear_status_button = page.get_by_text("Clear status")
    clear_status_button.click()
    # Immediately click on the page as defined in the bug reproduction steps.
    page.mouse.click(889, 480)
    page.wait_for_timeout(5000)

    # Verify that it is still on the profile page by checking the contact method
    contact_method_element = page.locator('div[dir="auto"]', has_text="Contact method")
    expect(contact_method_element).to_be_visible()


def test_profile_page_after_clear_status() -> None: 
    with sync_playwright() as playwright:
        browser = browser = playwright.chromium.launch(
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
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        page.goto("https://dev.new.expensify.com:8082/")
        page.wait_for_timeout(2000)
        # Step 1: Login user 
        login_user(page)

        # Step 2: Enter User Information
        enter_user_information(page)
        
        # Step 3: Reproduce scenario
        reproduce_scenario(page)

        page.wait_for_timeout(2000)

        context.close()
        browser.close()
