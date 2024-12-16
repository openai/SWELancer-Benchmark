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
    return f"turingtemp+82860019@gmail.com"


def login_user(p: PlaywrightContextManager, first_name="Milan", last_name="T") -> tuple[Browser, Page, str]:
    # Launch chromiun and open new page
    browser = p.chromium.launch(headless=True, args=[
        "--disable-web-security",
        "--disable-features=IsolateOrigins,site-per-process"
    ])
    page = browser.new_page()
    user_email = generate_random_email()

    page.goto("https://dev.new.expensify.com:8082/")
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()

    try:
        page.locator("button", has_text="Join").click()
    except Exception:
        pass
    try: 
        page.locator("button", has_text="Join").click() 
    except Exception:
        pass

    try:
        expect(page.locator("text=What do you want to do today?")).to_be_visible()

        # Step 4: Select 'Track and budget expenses' in onobarding page and click Continue
        page.locator("text='Track and budget expenses'").click()
        page.get_by_role("button", name="Continue").click()
        
        # Step 5: Enter first name, last name and click continue
        page.locator('input[name="fname"]').fill(first_name)
        page.locator('input[name="lname"]').fill(last_name)
        page.get_by_role("button", name="Continue").last.click()
    except:
        pass
        
    return browser, page, user_email


def test_check_selfdm_isbold():
    with sync_playwright() as p:
        browser, page, user_email = login_user(p)
        # Start tracing
        page.context.tracing.start(screenshots=True, snapshots=True, sources=True)

        try:
            # Step 2: Check if the self DM exists
            selfdm_span = page.locator('span', has_text="Milan T (you)")
            expect(selfdm_span).to_be_visible()
        
            # Step 3: Check the style of the selfdm name
            tag_style = selfdm_span.get_attribute("style")
            expected_tag_style = 'font-weight: 700;'
            assert expected_tag_style in tag_style, f"Expected self DM name to have '{expected_tag_style}', but got '{tag_style}'"
        except Exception as e:
            # Re-raise so that the test fails after we save the trace
            raise e
        finally:
            # Stop tracing and save the file
            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            page.context.tracing.stop(path=trace_path)

            # Clean the trace file
            trace_cleaner(trace_path)

            # Close the browser
            browser.close()
