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
    return f"expensifyapp97+99999988@gmail.com"


def login_user(p: PlaywrightContextManager, first_name="Milan", last_name="T") -> tuple[Browser, Page, str]:
    # Launch chromiun and open new page
    proxy = {"server": "http://127.0.0.1:8080/"}
    args = ["--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"]
    browser = p.chromium.launch(headless=True, args=args, proxy=proxy)
    page = browser.new_page()
    user_email = generate_random_email()

    # Step 1: Open expensify url
    page.goto('https://dev.new.expensify.com:8082/')

    # Step 2: Enter email and click continue
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()
    time.sleep(1)

    # Step 3: Click join button
    try:
        page.locator('button[tabindex="0"]').click()
        time.sleep(1)
    except Exception:
        pass
    expect(page.locator("text=What do you want to do today?")).to_be_visible()

    # Step 4: Select 'Track and budget expenses' in onobarding page and click Continue
    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()
    time.sleep(1)

    # Step 5: Enter first name, last name and click continue
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()
    time.sleep(1)

    return browser, page, user_email


def test_cursor_disabled():
    with sync_playwright() as p:
        browser, page, user_email = login_user(p)
        context = page.context
        # Start tracing
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        try:
            # Step 2: Open personal chat
            personal_chat = page.get_by_text(f"Milan T (you)")
            expect(personal_chat).to_be_visible()
            personal_chat.click()
            time.sleep(1)

            # Step 2: Click on "+" icon and click submit expense
            plus_create_icon = page.locator('button[aria-label="Create"]').last
            expect(plus_create_icon).to_be_visible()
            plus_create_icon.click()
            time.sleep(1)

            submit_expense_button = page.locator('div[aria-label="Assign task"]')
            expect(submit_expense_button).to_be_visible()
            submit_expense_button.click()
            time.sleep(1)

            page.get_by_role("textbox", name="Title").fill("Samuel")
            page.get_by_role("button", name="Next").click()
            page.get_by_role("button", name="Confirm task").click()
            page.get_by_role("checkbox", name="Task").click()

            # Locate the element using the aria-label attribute
            page.locator('div[aria-label="Chat message"]').last.click()
            element = page.locator('text="Description"')
            element.click()

            # Use evaluate to check the computed style for the 'cursor' property
            cursor_style = element.evaluate("element => window.getComputedStyle(element).cursor")

            # Assert that the cursor is 'default'
            assert cursor_style == 'default', f"Expected cursor to be disabled, but it was '{cursor_style}'"

            print(f"Cursor style: {cursor_style}")
        finally:
            # Stop tracing and save
            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            context.tracing.stop(path=trace_path)
            trace_cleaner(trace_path)
            browser.close()
}