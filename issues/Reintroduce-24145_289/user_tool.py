import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from json import tool
import time
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page

from utils.trace_cleaner import trace_cleaner  # <--- Added import

# Utility to generate a random email
def generate_random_email():
    return f"expensifyapp97+5646545646@gmail.com"


def login_user(p: PlaywrightContextManager, first_name="Milan", last_name="T") -> tuple[Browser, Page, str]:
    # Launch chromiun and open new pag
    browser = p.chromium.launch(channel="chrome", headless=True, slow_mo=2100, args=[
            "--ignore-certificate-errors",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ])
    page = browser.new_page()
    user_email = generate_random_email()
    first_name = 'John'
    last_name = 'Doe'

    # Step 1: Open expensify url
    page.goto('https://dev.new.expensify.com:8082/') 

    # Step 2: Enter email and click continue
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()
    

    # Step 3: Click join button
    try: 
        page.locator('button[tabindex="0"]').click() 
        
    except Exception:
        pass

    if page.locator("text=What do you want to do today?").count() == 1:  
        # Step 4: Select 'Track and budget expenses' in onobarding page and click Continue
        page.locator("text='Track and budget expenses'").click()
        page.get_by_role("button", name="Continue").click()
        

        # Step 5: Enter first name, last name and click continue
        page.locator('input[name="fname"]').fill(first_name)
        page.locator('input[name="lname"]').fill(last_name)
        page.get_by_role("button", name="Continue").last.click()


    return browser, page, user_email


def test_close_account_bottom_margin():
    with sync_playwright() as p:
        # Step 1: Login user
        browser, page, user_email = login_user(p)
        context = browser.new_context()

        # Start tracing
        context.tracing.start(
            title="test_close_account_bottom_margin",
            screenshots=True,
            snapshots=True,
            sources=True
        )
        try:
            # Step 2: Click on setting icon
            profile = page.locator('button[aria-label="My settings"]')
            expect(profile).to_be_visible()
            profile.click()

            # Step 3: Click on troubleshoot
            troubleshoot = page.locator('div[role="menuitem"]').nth(9)
            expect(troubleshoot).to_be_visible()
            troubleshoot.click()

            # Step 4: Click on forced offline button
            forced_offline = page.locator('button[aria-label="Force offline"]')
            expect(forced_offline).to_be_visible()
            forced_offline.click()

            # Step 5: Click on Security
            dob = page.locator('div[role="menuitem"]').nth(4)
            expect(dob).to_be_visible()
            dob.click()

            # Step 6: Click on close account button
            page.locator("text='Close account'").click()

            # Step 7: Navigate to Close account form button
            close_account = page.locator('button[role="button"]').last
            expect(close_account).to_be_visible()
            close_account_mb = close_account.evaluate(
                'element => window.getComputedStyle(element.parentElement).marginBottom'
            )

            if close_account_mb == '0px':
                assert True, 'Close account button does not moves up when offline.'
            else:
                assert False, 'Close account button moves up when offline.'

        except Exception as e:
            # Re-raise after we ensure the trace is captured
            raise e
        finally:
            # Stop tracing regardless of success/failure
            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            context.tracing.stop(path=trace_path)

            # Clean the trace file
            trace_cleaner(trace_path)

            # Close the browser
            browser.close()
