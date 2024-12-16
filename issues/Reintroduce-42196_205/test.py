import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page


URL = "https://127.0.0.1:8082/"


def initialize_page_context(p: PlaywrightContextManager) -> tuple[Browser, Page]:
    # Launch chromium and open a new page
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
    page.goto(URL)
    return browser, page


def login_user(page: Page, user_email, first_name="Milan", last_name="T") -> str:
    # Step 2: Enter email and click continue
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[data-listener="Enter"]', has_text="Continue").click()

    # Step 3: Click join button
    page.locator('button[data-listener="Enter"]', has_text="Join").click()

    # Step 4: Select 'Something else' in onboarding page and click Continue
    something_else_button = page.locator('div[aria-label="Something else"]')
    something_else_button.click()

    # Step 5: Enter first name, last name and click continue
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()

    return user_email


def logout_user(page: Page) -> str:
    account_settings_button = page.get_by_role("button", name="My Settings")
    account_settings_button.click()
    signout_button = page.get_by_role("menuitem", name="Sign out")
    signout_button.click()


def test_manual_expense_description_cursor_should_not_overlap_with_text_content():
    with sync_playwright() as p:
        # Login user

        browser, page = initialize_page_context(p)
        # Email of the first logged in user.
        email1 = login_user(page, "t56826807+1734030556@gmail.com", "User", "One")
        logout_user(page)

        # Login second user.
        email2 = login_user(page, "t56826807+1734030569@gmail.com", "User", "Two")

        # Submit a new expense
        create_button = page.locator(
            'button[aria-label="Start chat (Floating action)"]'
        )
        create_button.click()

        submit_expense_button = page.get_by_role("menuitem", name="Submit expense")
        submit_expense_button.click()

        # click Manual expense option
        manual_expense_button = page.get_by_role("button", name="Manual")
        manual_expense_button.click()

        # Enter expense amount
        page.get_by_placeholder("0").fill("100")
        page.locator("#numPadContainerView").get_by_role("button", name="Next").click()

        # Search user 1 to submit expense to.
        page.get_by_test_id("selection-list-text-input").click()
        page.get_by_test_id("selection-list-text-input").fill(email1)
        try:
            page.get_by_label("User One").click()
        except:
            page.get_by_label(email1).click()

        # Enter description.
        page.get_by_role("menuitem", name="Description").get_by_role("img").click()
        page.get_by_role("textbox", name="What's it for?").fill("> hey")

        # Verification step: Check to see if padding right is any non-zero value.
        blockquote_element = page.locator('span[data-type="blockquote"]')
        expect(blockquote_element).to_have_css("padding-right", "1px")

        browser.close()