import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
import pytest
import random
from playwright.sync_api import sync_playwright, expect
from playwright._impl._browser import Browser
from playwright._impl._page import Page

# This script will help you get started by logging you into the app!

# Utility to generate a random email
def generate_random_email():
    random_number = random.randint(1, 2**20)
    return f"personcheck292438@gmail.com"

def test_issue():
    with sync_playwright() as p:
        # Step 1: Login user 
        # Launch chromiun and open new page
        browser = p.chromium.launch(headless=True,args=[
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
            ],
        )
        page = browser.new_page()
        user_email = generate_random_email()

        # Step 1: Open expensify url
        page.goto('https://dev.new.expensify.com:8082/') 

        # Step 2: Enter email and click continue
        page.locator('input[type="email"]').fill(user_email)
        page.locator('button[tabindex="0"]').click()
        page.wait_for_timeout(1000)

        # Step 3: Click join button
        page.locator("button", has_text="Join").click()

        try:
            # Step 4: Select 'Track and budget expenses' in onobarding page and click Continue
            page.locator("text='Track and budget expenses'").click()
            page.get_by_role("button", name="Continue").click()
            page.wait_for_timeout(1000)

            # Step 5: Enter first name, last name and click continue
            page.locator('input[name="fname"]').fill("test")
            page.get_by_role("button", name="Continue").last.click()
            page.wait_for_timeout(1000)
        except:
            pass

        # Select personal chat room
        personal_chat = page.locator('button[aria-label="Navigates to a chat"]',has_text='(you)').last # if fails try with getByLabel
        expect(personal_chat).to_be_visible()
        personal_chat.click()
        page.wait_for_timeout(1000)

        # Open status
        page.locator('button[aria-label="My settings"][role="button"]').click()
        page.wait_for_timeout(1000)

        page.locator('button[aria-label="Status"][tabindex="0"]').click()
        page.wait_for_timeout(1000)

        # The 'Save' button should be clicked twice
        page.get_by_role("button", name="Save").dblclick()
        
        page.wait_for_timeout(1000)

        # If the profilepage is not visible
        # clicking "Save" button has redirected the page to Conversation Page.
        expect(page.locator('div[data-testid="ProfilePage"]')).to_be_visible()
        page.wait_for_timeout(2000)

        browser.close()