import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page

from utils.trace_cleaner import trace_cleaner


# Utility to generate a random email
def generate_random_email():
    return f"srkiitd+00998@gmail.com"


def login_user(p: PlaywrightContextManager, first_name="John", last_name="Doe") -> tuple[Browser, Page, str]:

    proxy = {"server": "http://127.0.0.1:8080/"}
    args = ["--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"]
    browser = p.chromium.launch(headless=True, proxy=proxy, args=args, slow_mo=1000)
    page = browser.new_page()

    user_email = generate_random_email()

    # Step 1: Open expensify url
    page.goto('https://dev.new.expensify.com:8082/concierge') 

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
    page.wait_for_timeout(5000)
    # Step 4: Select 'Track and budget expenses' in onboarding page and click Continue
    page.locator("text='Something else'").click()
    page.get_by_role("button", name="Continue").click()
    page.wait_for_timeout(1000)

    # Step 5: Enter first name, last name and click continue
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()
    page.wait_for_timeout(1000)
  
    return browser, page, user_email


def test_44235():
    with sync_playwright() as p:
        browser, page, user_email = login_user(p)
        context = page.context
        trace_path = "/app/expensify/user_tool/output_browser1.zip"
        context.tracing.start(screenshots=True, snapshots=True, sources=True)

        try:
            page.wait_for_timeout(2000)
            
            # Close "Get Started" button regarding onboarding video
            welcome_expensify_btn = page.locator('button[role="button"]', has_text="Get started")
            if welcome_expensify_btn.count() == 1:
                welcome_expensify_btn.click()

            page.wait_for_timeout(5000)
            
            concierge_chat = page.locator('button[aria-label="Navigates to a chat"]', has_text='Concierge').last
            expect(concierge_chat).to_be_visible()
            concierge_chat.click()
            
            concierge_chat_title = page.get_by_label("Concierge", exact=True)
            expect(concierge_chat_title).to_be_visible()

            page.wait_for_timeout(1000)
        except Exception as e:
            # Re-raise so the test properly fails while still ensuring the trace is captured.
            raise e
        finally:
            context.tracing.stop(path=trace_path)
            trace_cleaner(trace_path)
            browser.close()
