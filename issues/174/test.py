import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page



def generate_random_email():
    timestamp = int(time.time())
    return f"milan.thummar-{timestamp}@gmail.com"


def login_user(p: PlaywrightContextManager, first_name="Milan", last_name="T") -> tuple[Browser, Page, str]:


    browser = p.chromium.launch(channel="chrome",
        headless=True,
        args=[
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ])

    page = browser.new_page()
    user_email = generate_random_email()


    page.goto('https://dev.new.expensify.com:8082/') 


    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(5000)


    page.locator('button[tabindex="0"]').click() 
    page.wait_for_timeout(10000)
    

    try:    
        expect(page.locator("text=What do you want to do today?")).to_be_visible()

        page.locator("text='Track and budget expenses'").click()
        page.get_by_role("button", name="Continue").click()
        page.wait_for_timeout(1000)


        page.locator('input[name="fname"]').fill(first_name)
        page.locator('input[name="lname"]').fill(last_name)
        page.get_by_role("button", name="Continue").last.click()
        page.wait_for_timeout(1000)
    except Exception as err:
        pass

    return browser, page, user_email


def test_settings_header_style():
    with sync_playwright() as p:

        browser, page, user_email = login_user(p)


        my_settings_button = page.locator('button[aria-label="My settings"]')
        expect(my_settings_button).to_be_visible()
        my_settings_button.click()
        page.wait_for_timeout(1000)

        workspace_settings_button = page.locator('div[aria-label="Workspaces"][role="menuitem"]')
        expect(workspace_settings_button).to_be_visible()
        workspace_settings_button.click()
        page.wait_for_timeout(1000)


        rocket_icon = page.locator("div:nth-child(4) > div:nth-child(2) > div:nth-child(2) > div > div > div > div > div > div > div > div > div:nth-child(2) > div > div > svg")
        expect(rocket_icon).to_be_visible()


        h1_styled_title = page.locator('div[style*="font-size: 22px;"]', has_text="Create a workspace")
        expect(h1_styled_title).to_be_visible()

        page.wait_for_timeout(2000)

        browser.close()

