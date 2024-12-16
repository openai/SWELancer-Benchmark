import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager, Playwright
from playwright._impl._browser import Browser
from playwright._impl._page import Page
import re

EMAIL = "t1533148@gmail.com" # for example test+1234@gmail.com


# Utility to generate a random email
def generate_random_email():
    return "t1533148+1734041051@gmail.com"


def login_user(p: Playwright, first_name="Milan", last_name="T") -> tuple[Browser, Page, str]:
    # Launch chromiun and open new page
    browser = p.chromium.launch(headless=True, slow_mo = 1000,
            proxy = {"server": "http://127.0.0.1:8080/"},
            args=[
            "--ignore-certificate-errors",
            "--disable-web-security", 
            "--disable-features=IsolateOrigins,site-per-process"
        ])
    context_args = {}
    context_args["geolocation"] = {"latitude": 37.7749, "longitude": 122.4194}
    context_args["permissions"] = ["geolocation"]
    context_args["ignore_https_errors"] = True
    context = browser.new_context(**context_args)

    # Create a new page in the appropriate context
    page = context.new_page()
    page.wait_for_timeout(5000)
    user_email = generate_random_email()

    # Step 1: Open expensify url
    page.goto('https://127.0.0.1:8082/') 

    # Step 2: Enter email and click continue
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()

    # Step 3: Click join button
    try: 
        page.locator('button[tabindex="0"]').click() 
    except Exception:
        pass
        
    # Step 4: Select 'Track and budget expenses' in onobarding page and click Continue
    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()
    # Step 5: Enter first name, last name and click continue
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()
    page.wait_for_timeout(2000)

    return browser, page, user_email


def test_welcome_group_message():
    with sync_playwright() as p:
        
        first_name = 'Aohn'
        last_name = 'Doe'
        
        users = [
            'donaldtrump+98@gmail.com',
            'elonmusk+98@gmail.com',
            'pillgates+98@gmail.com',
        ]
        
        # Step 1: Login user 
        browser, page, user_email = login_user(p, first_name, last_name)

        # Step 3: Click on + icon and click on "Start chat"
        page.get_by_label("Start chat (Floating action)").click()
        page.wait_for_timeout(1000)
        
        # Start Chat
        page.get_by_text("Start chat").click()
        page.wait_for_timeout(1000)
        
        # Steps to add multiple users to the group
        username, domain = EMAIL.split('@')
        for i in range(3):
            email = f"{username}{i}@{domain}"
            # Fill in the email field and click "Add to group"
            input_field = page.locator('input[data-testid="selection-list-text-input"]')
            input_field.fill(email)
            page.wait_for_timeout(1000)
            page.locator('button:has(div:text("Add to group"))').nth(1).click()
            page.wait_for_timeout(1000)
            
        page.get_by_role("button", name="Next").click()
        page.get_by_role("button", name="Start group").click()
        page.wait_for_timeout(1000)
        welcome_message = page.locator('div[aria-label="Chat welcome message"]').all_inner_texts()
        page.get_by_label(f"Aohn, {username}0@{domain}, {username}1@{domain}, {username}2@{domain}").click()
        page.locator("div").filter(has_text=re.compile(r"^Members$")).nth(3).click()
        page.locator('button[aria-label="Hidden"][role="button"][data-tag="pressable"]').nth(2).click()
        page.get_by_role("button", name="Remove from group").click()
        page.get_by_role("button", name="Remove", exact=True).click()
        page.get_by_test_id("ReportParticipantsPage").get_by_label("Back").click()
        page.get_by_label("Back").nth(-1).click()
        # Step 6: check if user email is displayed in welcome message
        welcome_msg = page.locator('div[aria-label="Chat welcome message"]')
        is_user_deleted = welcome_msg.get_by_text("t15331481@gmail.com").is_visible()
        page.wait_for_timeout(2000)
        
        if is_user_deleted:
            assert False, 'The removed user is displayed in the welcome group message'
        else:
            assert True, 'The removed user is not displayed in the welcome group message'

        page.wait_for_timeout(6000)
        browser.close()