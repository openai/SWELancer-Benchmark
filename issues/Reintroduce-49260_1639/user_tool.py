import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page

from utils.trace_cleaner import trace_cleaner

# Utility to generate a random email
def generate_random_email():
    timestamp = 4926049260
    return f"expensify624+{timestamp}@gmail.com"


def login_user(p: PlaywrightContextManager, first_name="Abhishek", last_name="M") -> tuple[Browser, object, Page, str]:
    # Launch chromium and open new context with tracing
    browser = p.chromium.launch(headless=True, args=[
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
        ])
    context = browser.new_context()
    context.tracing.start(screenshots=True, snapshots=True, sources=True)

    page = context.new_page()
    user_email = generate_random_email()

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
    except:
        pass

    return browser, context, page, user_email


def test_the_issue():
    with sync_playwright() as p:
        browser, context, page, user_email = login_user(p)
        try:
            page.wait_for_timeout(1000)
            page.get_by_label("My settings").click()
            page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").get_by_text("Workspaces").click()
            page.get_by_label("New workspace").last.click()
            page.get_by_label("Members").last.click()
            page.get_by_role("button", name="Invite member").click()
            page.get_by_test_id("selection-list-text-input").fill("test3@gmail.com")
            page.wait_for_timeout(1000)
            page.get_by_label("test3@gmail.com").last.click()
            page.get_by_test_id("selection-list-text-input").fill("test5@gmail.com")
            page.wait_for_timeout(1000)
            page.get_by_label("test5@gmail.com").last.click()
            page.wait_for_timeout(1000)
            page.keyboard.press("Enter")
            page.wait_for_timeout(1000)
            page.keyboard.press("Enter")
            page.keyboard.press("Tab")
            page.keyboard.press("Enter")
            page.wait_for_timeout(1000)
            page.get_by_label("Back").last.click()
            page.get_by_label("Inbox").last.click()
            page.get_by_label("My settings").last.click()
            page.wait_for_timeout(1000)
            page.locator('div[role="menuitem"][aria-label="Troubleshoot"]').last.click()
            page.wait_for_timeout(3000)
            page.locator('div[aria-label="Clear cache and restart"]').last.click()
            page.get_by_role("button", name="Reset and refresh").last.click()
            page.wait_for_timeout(3000)
            page.get_by_label("Inbox").click()
            page.wait_for_timeout(3000)
            expect(page.locator('button[aria-label="Navigates to a chat"]', has_text="Chat Report").last).not_to_be_visible()
        except:
            # Optionally re-raise after capturing, or just pass
            raise
        finally:
            # Always stop tracing and clean
            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            browser.close()
