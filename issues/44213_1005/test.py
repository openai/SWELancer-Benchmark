import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page

# Utility to generate a random email
def generate_random_email():
    timestamp = int(time.time())
    return "kenworktestemail+828@gmail.com"


def login_user(p: PlaywrightContextManager, first_name="Ayush", last_name="G") -> tuple[Browser, Page, str]:
    # Launch chromiun and open new page
    browser = p.chromium.launch(headless=True, devtools=True, args=["--disable-web-security",
        "--disable-features=IsolateOrigins, site-per-process"])
    page = browser.new_page()
    user_email = generate_random_email()

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
    except Exception:
        pass
        
    # Step 4: Select 'Track and budget expenses' in onobarding page and click Continue
    if page.locator("text='Track and budget expenses'"):
        page.locator("text='Track and budget expenses'").click()
        page.get_by_role("button", name="Continue").click()

    # Step 5: Enter first name, last name and click continue
        page.locator('input[name="fname"]').fill(first_name)
        page.locator('input[name="lname"]').fill(last_name)
        page.get_by_role("button", name="Continue").last.click()

        try:
            get_started_button = page.locator('text="Get started"')
            expect(get_started_button).to_be_visible()
            get_started_button.click()
        except Exception:
            pass
        
    return browser, page, user_email


def test_console_error():
    with sync_playwright() as p:
        page_errors = []
        browser, page, user_email = login_user(p)        
        page.on("pageerror", lambda message: page_errors.append(message))

        page.locator('span:text("Ayush G (you)")').click()

        error_count_before_click = len(page_errors)

        # Get the current URL of the page
        current_url = page.url

        page.get_by_role("textbox").fill(f"{current_url}/duplicates/review")
        page.get_by_role("button", name="Send").click()
        page.wait_for_timeout(3000)
        page.get_by_test_id("a").click()

        try:
            not_here_page_div = page.locator(f'div:text("Hmm... it\'s not here")')
            expect(not_here_page_div).to_be_visible()
        except Exception as e:
            page.get_by_role("button", name="Keep all").click()

        page.wait_for_timeout(3000)

        # Calculating number of console errors after click
        error_count_after_click = len(page_errors)
        assert error_count_before_click == error_count_after_click

        browser.close()

