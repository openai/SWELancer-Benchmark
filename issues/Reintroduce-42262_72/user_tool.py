import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page
from utils.trace_cleaner import trace_cleaner


def login_user(p: PlaywrightContextManager, user_email: str, first_name="Milan", last_name="T") -> tuple[Browser, Page]:
    # Launch chromiun and open new page
    browser = p.chromium.launch(headless=True, slow_mo = 1000,
        proxy = {"server": "http://127.0.0.1:8080/"},
        args=[
        "--ignore-certificate-errors",
        "--disable-web-security", 
        "--disable-features=IsolateOrigins,site-per-process"
    ])
    context_args = {}
    context_args["geolocation"] = {"latitude": 37.7749, "longitude": 122.4194}
    context_args["permissions"] = ["geolocation"]
    context_args["ignore_https_errors"] = True
    context = browser.new_context(**context_args)
    page = context.new_page()
    page.wait_for_timeout(5000)
    page.goto("https://127.0.0.1:8082/")
    # Step 2: Enter email and click continue
    page.locator('input[type="email"]').fill(user_email)
    page.get_by_test_id("username").press("Enter")
    page.wait_for_timeout(1000)

    # Step 3: Click join button
    page.get_by_role("button", name="Join").click()
         
    # Step 4: Select 'Track and budget expenses' in onobarding page and click Continue
    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()
    page.wait_for_timeout(1000)

    # Step 5: Enter first name, last name and click continue
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()
    page.wait_for_timeout(1000)

    try:
        get_started_button = page.locator('text="Get Started"')
        get_started_button.click()
        page.wait_for_timeout(1000)
    except Exception:
        pass

    return browser, page


def test_save_description_in_submitted_expense():
    with sync_playwright() as p:
        browser, page = login_user(p, 'rgarciatammy4+1734100237@gmail.com')
        context = page.context
        # Start tracing
        context.tracing.start(screenshots=True, snapshots=True)
        try:
            # Step 2: Click on + icon and click on "New workspace"
            page.get_by_label("My settings").click()
            page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").get_by_text("Workspaces").click()
            page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()
            page.locator('button[aria-label="New workspace"][role="button"][data-tag="pressable"]').nth(0).click()
            page.locator('div[aria-label="Members"]').nth(0).click()
            page.get_by_role("button", name="Invite member").click()

            email_input = page.locator('div[aria-label="Name, email, or phone number"] >> input')

            invitee_email_id = "rgarciatammy4+02934809@gmail.com"
            email_input.fill(invitee_email_id)
            page.wait_for_timeout(1000)

            email_dropdown = page.locator(f'div:text("{invitee_email_id}")').nth(1)
            email_dropdown.click()
            page.wait_for_timeout(2000)

            next_button = page.locator('div:text("Next")')
            next_button.click()
            page.wait_for_timeout(1000)

            invite_button = page.locator('text="Invite"')
            invite_button.click()
            page.wait_for_timeout(1000)

            # Step 3: Click on Back arrow to go back and navigate to inbox screen
            back_arrow_button = page.locator('button[aria-label="Back"]')
            back_arrow_button.click()

            inbox_menu = page.locator('button[aria-label="Inbox"]')
            inbox_menu.click()
            page.wait_for_timeout(2000)

            chat_button = page.locator(f'button[aria-label="Navigates to a chat"] >> div:text-is("{invitee_email_id}")')
            chat_button.click()
            page.wait_for_timeout(2000)
         
            back_arrow_button = page.locator(f'button[aria-label="{invitee_email_id}"]')
            back_arrow_button.click()
            page.wait_for_timeout(2000)

            group_members_count_div = page.locator('div:text-is("2")')
            expect(group_members_count_div).to_be_visible()
            group_members_count_div.click()
            page.wait_for_timeout(2000)

        finally:
            # Stop tracing and clean it up
            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            browser.close()
