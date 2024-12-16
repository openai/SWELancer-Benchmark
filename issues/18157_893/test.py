import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
from datetime import datetime
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page


# Utility to generate a random email
def generate_random_email():
    return "testerbro7077+8699649@gmail.com"


def login_user(p: PlaywrightContextManager, first_name="Milan", last_name="T") -> tuple[Browser, Page, str]:
    # Launch chromiun and open new page
    browser = p.chromium.launch(channel="chrome", headless=True, args=[
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ])
    page = browser.new_page()
    user_email = generate_random_email()

    # Step 1: Open expensify url
    page.goto('https://dev.new.expensify.com:8082/') 

    # Step 2: Enter email and click continue
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()
    time.sleep(1)

    # Step 3: Click join button
    try: 
        page.locator('button[tabindex="0"]').click() 
        time.sleep(1)
    except Exception:
        pass
    try:

        expect(page.locator("text=What do you want to do today?")).to_be_visible()
        # page.pause()
        
        # Step 4: Select 'Track and budget expenses' in onobarding page and click Continue
        page.locator("text='Track and budget expenses'").click()
        page.get_by_role("button", name="Continue").click()
        time.sleep(1)

        # Step 5: Enter first name, last name and click continue
        page.locator('input[name="fname"]').fill(first_name)
        page.locator('input[name="lname"]').fill(last_name)
        page.get_by_role("button", name="Continue").last.click()
        time.sleep(1)
    except:
        pass

    return browser, page, user_email


def test_character_limit_in_address_field():
    with sync_playwright() as p:
        # Step 1: Login user 
        browser, page, user_email = login_user(p)
        
        setting_icon = page.get_by_label("My settings")
        expect(setting_icon).to_be_visible()
        setting_icon.click()
        time.sleep(1)

        # Locate address field
        page.locator('div:has-text("Address")').last.click()
        address_field = page.get_by_label("Address line 1").get_by_role("textbox")
        address_field.click()

        address_field.fill("we can close this to focus on more urgent issue this is just a minor viewing discrepancy ~we can close this to focus on more urgent")

        # Get the value of the input field
        actual_value = address_field.input_value()

        expected_value = "we can close this to focus on more urgent issue th"

        # Validate the value of the input field
        assert actual_value == expected_value, (
            f"Expected '{expected_value}' but got '{actual_value}'"
        )

        # Close the browser
        browser.close()