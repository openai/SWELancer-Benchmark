import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page

SITE_URL = "https://dev.new.expensify.com:8082/"
PRIMARY_EMAIL = "expensifyolddot+1733039252@gmail.com"
FIRST_NAME = "expensifyolddot"
LAST_NAME = "1733039252"

def login_user(p: PlaywrightContextManager, first_name="Milan", last_name="T") -> tuple[Browser, Page, str]:
    # Launch Chromium and open a new page
    browser = p.chromium.launch(headless=True,
        proxy={'server': 'http://127.0.0.1:8080'},
        args=[
            '--ignore-certificate-errors',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
        ],
    )
    context = browser.new_context(
            viewport={"width": 360, "height": 640},  # Phone screen dimensions
            user_agent="Mozilla/5.0 (Linux; Android 10; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Mobile Safari/537.36",  # Mobile user agent
            is_mobile=True,
            has_touch=True,
            ignore_https_errors=True
        )
    page = context.new_page()
    user_email = PRIMARY_EMAIL

    # Step 1: Open expensify url
    page.goto(SITE_URL)

    # Step 2: Enter email and click continue
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(2000)

    # Step 3: Click join button
    try: 
        page.locator('button[tabindex="0"]').click() 
    except Exception:
        pass

    if page.locator("text=What do you want to do today?").is_visible():
        # Step 4: Select 'Track and budget expenses' in onbarding page and click Continue
        page.locator("text='Track and budget expenses'").click()
        page.get_by_role("button", name="Continue").click()

        # Step 5: Enter first name, last name and click continue
        page.locator('input[name="fname"]').fill(first_name)
        page.locator('input[name="lname"]').fill(last_name)
        page.get_by_role("button", name="Continue").last.click()
        page.wait_for_timeout(2000)

    return browser, page, context, user_email


def test_create_workspace():
    with sync_playwright() as p:
        # Step 1: Login user
        browser, page, context, user_email = login_user(p, FIRST_NAME, LAST_NAME)

        # Step 2: Create a new workspace
        
        # if there close visible then only click it
        if page.get_by_label("Close").is_visible():
            page.get_by_label("Close").click()
        page.get_by_label("Workspaces").click()
        page.get_by_label("New workspace").click()

    
        # Step 3: Navigate back and verify the user is taken back to the workspace switcher page
        page.get_by_test_id("WorkspaceInitialPage").get_by_label("Back").click()
        # Wait until the URL becomes the expected URL
        expected_url = "https://dev.new.expensify.com:8082/workspace-switcher"
        page.wait_for_url(expected_url)
        # Assert that the current URL is the expected one
        assert page.url == expected_url, f"Expected URL to be {expected_url}, but got {page.url}"

        # ---------------------
        context.close()
        browser.close()