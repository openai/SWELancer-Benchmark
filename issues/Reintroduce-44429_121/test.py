import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page
import platform

# Gmail credentials for generating user info
GMAIL_NAME = "milan.thummar"
GMAIL_APP_PASSWORD = "example_password"  # Replace with actual app password if needed

# Utility to generate user info
def get_test_user_info(seed=None, first_name=None, last_name=None):
    if first_name is None:
        first_name = GMAIL_NAME.split(".")[0].capitalize()
    if last_name is None:
        last_name = ""
    email = f"{GMAIL_NAME}+{seed}@gmail.com" if seed is not None else f"{GMAIL_NAME}@gmail.com"
    return {"email": email, "password": GMAIL_APP_PASSWORD, "first_name": first_name, "last_name": last_name}


def login_user(p: PlaywrightContextManager, first_name="A", last_name="Khan") -> tuple[Browser, Page, str]:
    # Launch chromiun and open new page
    browser = p.chromium.launch(channel="chrome", slow_mo=2000,headless=True, args=[
        "--disable-web-security",
        "--disable-features=IsolateOrigins,site-per-process",
        "--ignore-certificate-errors",
    ])
    page = browser.new_page()
    user_info = get_test_user_info(seed=int(time.time()), first_name=first_name, last_name=last_name)
    user_email = user_info["email"]

    # Step 1: Open expensify url
    page.goto('https://dev.new.expensify.com:8082/')

    # Step 2: Enter email and click continue
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(1000)

    # Step 3: Click join button
    try:
        page.locator('button[tabindex="0"]').click()
        page.wait_for_timeout(1000)
    except Exception:
        pass

    expect(page.locator("text=What do you want to do today?")).to_be_visible()

    try:
        # Step 4: Select 'Track and budget expenses' in onobarding page and click Continue
        page.locator("text='Track and budget expenses'").click()
        page.get_by_role("button", name="Continue").click()
        page.wait_for_timeout(1000)

        # Step 5: Enter first name, last name and click continue
        page.locator('input[name="fname"]').fill(first_name)
        page.locator('input[name="lname"]').fill(last_name)
        page.get_by_role("button", name="Continue").last.click()
        page.wait_for_timeout(1000)
    except Exception:
        pass
    
    return browser, page, user_email


def test_submit_expense_domain_recipient():
    with sync_playwright() as p:
        # Step 1: Login user
        browser, page, user_email = login_user(p)

        # Step 2: Click on + icon and click on "Submit Expense"
        plus_icon = page.locator('button[aria-label="Start chat (Floating action)"]')
        expect(plus_icon).to_be_visible()
        plus_icon.click()

        # Step 3: Click on the "Submit Expense" button
        submit_expense_button = page.locator('div[aria-label="Submit expense"]')
        expect(submit_expense_button).to_be_visible()
        submit_expense_button.click()

        # Step 4: Click on "Manual" button and enter amount
        manual_button = page.locator('button[aria-label="Manual"]')
        expect(manual_button).to_be_visible()
        manual_button.click()

        # Step 5: Fill in an amount
        page.locator('input[role="presentation"]').fill("20")

        # Step 6: Click on Next button
        next_button = page.locator("#numPadContainerView").get_by_role("button", name="Next")
        expect(next_button).to_be_visible()
        next_button.click()

        # Step 7: Input recipient email
        input_recipient = page.get_by_test_id("selection-list-text-input")
        expect(input_recipient).to_be_visible()
        input_recipient.fill("+@applause.expensifail.com")
        # Step 8: Wait for 3 seconds
        page.wait_for_timeout(3000)

        # Step 9: Verify that no results found message is displayed
        expect(page.get_by_text("No results found")).to_be_visible()

        browser.close()

