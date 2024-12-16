import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page

from utils.trace_cleaner import trace_cleaner


def login_user(p: PlaywrightContextManager, first_name="Milan", last_name="T") -> tuple[Browser, Page, str]:
    # Launch Chromium browser and open a new page
    browser = p.chromium.launch(headless=True, args=[
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ])
    page = browser.new_page()
    user_email = "freelanceapptest+1733261135@gmail.com"

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
    expect(page.locator("text=What do you want to do today?")).to_be_visible()

    # Step 4: Select 'Track and budget expenses' on the onboarding page and click Continue
    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()
    page.wait_for_timeout(1000)

    # Step 5: Enter first name, last name and click continue
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()
    page.wait_for_timeout(1000)

    return browser, page, user_email


def open_submit_expense_and_click_on_next_button(
    browser: Browser,
    page: Page,
    user_email: str,
) -> tuple[Browser, Page, str]:
    plus_icon = page.locator('button[aria-label="Start chat (Floating action)"]')
    expect(plus_icon).to_be_visible()
    plus_icon.click()
    page.wait_for_timeout(1000)

    new_workspace_button = page.locator('div[aria-label="Submit expense"]')
    expect(new_workspace_button).to_be_visible()
    new_workspace_button.click()
    page.wait_for_timeout(1000)

    manual_button = page.locator('button[aria-label="Manual"]')
    expect(manual_button).to_be_visible()
    manual_button.click()
    page.wait_for_timeout(1000)

    page.get_by_placeholder("0").fill("0")
    page.locator("#numPadContainerView").get_by_role("button", name="Next").click()
    page.wait_for_timeout(2000)

    return browser, page, user_email


def test_error_message_top_margin():
    with sync_playwright() as p:
        browser = None
        page = None
        user_email = None
        context = None
        try:
            # Step 1: Login user
            browser, page, user_email = login_user(p)

            # Start Playwright trace recording
            context = page.context
            context.tracing.start(screenshots=True, snapshots=True, sources=True)

            # Step 2: Open submit expense RHN
            browser, page, user_email = open_submit_expense_and_click_on_next_button(browser, page, user_email)

            # Step 3: Locate the error message and the next button
            error_message = page.get_by_text("Please enter a valid amount before continuing.", exact=True)
            next_button = page.locator("#numPadContainerView").get_by_role("button", name="Next")
            page.wait_for_timeout(1000)

            # Step 4: Calculate the vertical distance between the bottom of the error message and the top of the next button
            error_message_box = error_message.bounding_box()
            next_button_box = next_button.bounding_box()

            # Ensure both bounding boxes exist before calculating distances
            assert error_message_box is not None, "Error message bounding box not found."
            assert next_button_box is not None, "Next button bounding box not found."

            # Step 5: Calculate the distance between the bottom of the error message and the top of the next button
            distance_between_elements = next_button_box['y'] - (error_message_box['y'] + error_message_box['height'])

            # Step 6: Assert the distance is as expected (12 px)
            print(f"Distance between elements: {distance_between_elements}px")
            assert distance_between_elements == 14, f"Expected 14px distance, but found {distance_between_elements}px"
            page.wait_for_timeout(1000)
        finally:
            # Stop trace and clean it even if the test fails
            if context:
                context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
                trace_cleaner("/app/expensify/user_tool/output_browser1.zip")

            if browser:
                browser.close()
