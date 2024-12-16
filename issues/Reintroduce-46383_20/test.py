import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page

static_email = "testuserexpensify1+113@gmail.com"


def login_user(p: PlaywrightContextManager, first_name="Milan", last_name="T") -> tuple[Browser, Page, str]:
    # Launch Chromium and open a new page
    browser = p.chromium.launch(channel="chrome", headless=True, args=["--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"],slow_mo=1000)
    context = browser.new_context(
            viewport={"width": 360, "height": 640},  # Phone screen dimensions
            user_agent="Mozilla/5.0 (Linux; Android 10; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Mobile Safari/537.36",  # Mobile user agent
            is_mobile=True,
            has_touch=True,
            ignore_https_errors=True
        )
    page = context.new_page()
    user_email = static_email

    # Step 1: Open expensify url
    page.goto('https://dev.new.expensify.com:8082/') 

    # Step 2: Enter email and click continue
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()
    

    # Step 3: Click join button
    try: 
        page.get_by_role("button", name="Join").click()
    except Exception:
        pass
        
    # Step 4: Select 'Track and budget expenses' in onbarding page and click Continue
    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()
    

    # Step 5: Enter first name, last name and click continue
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()
    

    return browser, page, context, user_email


def test_create_workspace():
    with sync_playwright() as p:
        # Step 1: Login user
        browser, page, context, user_email = login_user(p)

        # Step 2: Create a new workspace
        page.get_by_label("Close").click()
        page.get_by_label("Workspaces").click()
        page.get_by_label("New workspace").click()

    
        # Step 3: Navigate back and verify redirection to the workspace switcher page
        back_button = page.get_by_test_id("WorkspaceInitialPage").get_by_label("Back")
        back_button.click()

        # Define the expected URL for workspace switcher page
        expected_url = "https://dev.new.expensify.com:8082/workspace-switcher"

        # Wait until the URL matches the expected URL
        page.wait_for_url(expected_url)

        # Validate that the current URL matches the expected URL
        assert page.url == expected_url, f"Error: Expected URL '{expected_url}', but found '{page.url}'"

        context.close()
        browser.close()

