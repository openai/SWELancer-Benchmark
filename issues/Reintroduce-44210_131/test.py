import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page

# Gmail credentials for generating user info
GMAIL_NAME = "rgulraiz2000"
GMAIL_APP_PASSWORD = "kepw uquj myoa npvj"

# Utility to generate user info
def get_test_user_info(seed=None, first_name=None, last_name=None):
    if first_name is None:
        first_name = GMAIL_NAME.split(".")[0].capitalize()
    if last_name is None:
        last_name = ""
    email = f"{GMAIL_NAME}+{seed}@gmail.com" if seed is not None else f"{GMAIL_NAME}@gmail.com"
    return {"email": email, "password": GMAIL_APP_PASSWORD, "first_name": first_name, "last_name": last_name}

def login_user(p: PlaywrightContextManager, first_name="Milan", last_name="T") -> tuple[Browser, Page, str]:
    # Launch Chromium and open new page
    browser = p.chromium.launch(channel="chrome", headless=True, slow_mo=2000, args=[
        "--disable-web-security",
        "--disable-features=IsolateOrigins,site-per-process",
    ])
    page = browser.new_page()
    user_info = get_test_user_info(seed=int(time.time()), first_name=first_name, last_name=last_name)
    user_email = user_info["email"]

    # Step 1: Open Expensify URL
    page.goto('https://dev.new.expensify.com:8082/')

    # Step 2: Enter email and click continue
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(1000)

    # Step 3: Click join button
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(1000)
    expect(page.locator("text=What do you want to do today?")).to_be_visible()

    # Step 4: Select 'Track and budget expenses' in onboarding page and click Continue
    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()
    page.wait_for_timeout(1000)

    # Step 5: Enter first name, last name, and click continue
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()
    page.wait_for_timeout(1000)

    return browser, page, user_email

def test_settings_header_style():
    with sync_playwright() as p:
        # Step 1: Login user 
        browser, page, user_email = login_user(p)

        # Step 2: Go to workspace settings
        my_settings_button = page.locator('button[aria-label="My settings"]')
        expect(my_settings_button).to_be_visible()
        my_settings_button.click()
        page.wait_for_timeout(1000)

        workspace_settings_button = page.locator('div[aria-label="Workspaces"][role="menuitem"]')
        expect(workspace_settings_button).to_be_visible()
        workspace_settings_button.click()
        page.wait_for_timeout(1000)

        # Step 3: Rocket icon should be visible in header
        rocket_icon = page.locator("div:nth-child(4) > div:nth-child(2) > div:nth-child(2) > div > div > div > div > div > div > div > div > div:nth-child(2) > div > div > svg")
        expect(rocket_icon).to_be_visible()

        # Step 4: "Create new workspace" should be visible in h1 (font-size=24px)
        h1_styled_title = page.locator('div[style*="font-size: 22px;"]', has_text="Create a workspace")
        expect(h1_styled_title).to_be_visible()

        page.wait_for_timeout(2000)

        browser.close()
