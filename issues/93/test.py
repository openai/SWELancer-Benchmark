from email.header import decode_header
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page

NEW_DOT_URL = "https://dev.new.expensify.com:8082/"

# Utility to generate an email
def generate_email():
    timestamp = 528940003
    return f"freelanceapptest+{timestamp}@gmail.com"

# Function to log in to an existing account
def login_to_existing_account(page, user_email):
    # Step 1: Navigate to the Expensify new development environment login page
    page.goto(NEW_DOT_URL)
    page.wait_for_timeout(2000)

    # Step 2: Enter the email address and proceed to login
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(1000)

    #Step 3: Fetch and fill in the Magic Code
    magic_code = '120730'
    validate_code_input = page.locator('input[data-testid="validateCode"]')
    expect(validate_code_input).to_be_visible()
    validate_code_input.fill(magic_code)

    page.wait_for_timeout(2000)

    return page

def test_refresh_on_onboarding_accounting():
    with sync_playwright() as p:
    # Launch Chromium and open a new page
        browser = p.chromium.launch(
            proxy = {"server": "http://localhost:8080"}, headless = False, args = ["--no-sandbox", "--disable-dev-shm-usage", "--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"], slow_mo = 2000, channel = "chromium")

        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        user_email = generate_email()

        # Step 1: Log in to the account whose onboarding was in old_dot and was abandoned using the new_dot URL
        page = login_to_existing_account(page, user_email=user_email)

        errors = []

        # Step 2: Go to the onboarding page and get the initial count of workspaces
        page.goto(NEW_DOT_URL + "onboarding/accounting")
        page.wait_for_timeout(2000)

        new_workspace_chat_button = page.locator(f'//button[@aria-label="Navigates to a chat"]//div[contains(text(), "{user_email}")]')
        initial_count = new_workspace_chat_button.count()

        if initial_count != 1:
            errors.append(f"❌ Expected 1 workspace, but found {initial_count}. Reopening onboarding in new_dot after abandoning on old_dot, creates a new workspace")

        # Step 3: Reload and verify count remains the same
        page.reload()
        page.wait_for_timeout(2000)

        new_count_after_reload = new_workspace_chat_button.count()

        if new_count_after_reload > initial_count:
            errors.append("❌ A new workspace was created on page refresh!")

        # Step 4: Navigate to new_dot URL
        page.goto(NEW_DOT_URL)
        page.wait_for_timeout(2000)

        new_count_after_navigation = new_workspace_chat_button.count()

        if new_count_after_navigation > initial_count:
            errors.append("❌ A new workspace was created after navigating to base new_dot url!")

        # Step 5: Assert no errors; otherwise, raise all errors
        if errors:
            raise AssertionError("\n".join(errors))

        page.wait_for_timeout(1000)

        # Close browser
        browser.close()
