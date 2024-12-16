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
    return 'freelanceapptest+1734086020@gmail.com'


def login_user(p: PlaywrightContextManager, first_name="Milan", last_name="T") -> tuple[Browser, Page, str]:
    # Launch Chromium and open a new page
    browser = p.chromium.launch(channel="chrome", headless=True, args=["--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"], slow_mo=1000)
    context = browser.new_context(
        viewport={"width": 360, "height": 640},  # Phone screen dimensions
        user_agent="Mozilla/5.0 (Linux; Android 10; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Mobile Safari/537.36",  # Mobile user agent
        is_mobile=True,
        has_touch=True,
        ignore_https_errors=True
    )
    page = context.new_page()
    user_email = generate_random_email()

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
    expect(page.locator("text=What do you want to do today?")).to_be_visible()

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
        browser, page, context, user_email = login_user(p)

        # Start tracing
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        try:
            # Step 2: Create a new workspace
            page.get_by_label("Close").click()
            page.get_by_label("Workspaces").click()
            page.get_by_label("New workspace").click()

            # Step 3: Navigate back and verify the user is taken back to the workspace switcher page
            page.get_by_test_id("WorkspaceInitialPage").get_by_label("Back").click()
            expected_url = "https://dev.new.expensify.com:8082/workspace-switcher"
            page.wait_for_url(expected_url)
            assert page.url == expected_url, f"Expected URL to be {expected_url}, but got {page.url}"
        finally:
            # Stop tracing and clean up the trace regardless of success or failure
            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")

            # Close context and browser
            context.close()
            browser.close()
