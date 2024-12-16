import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page


# Utility to generate a random email
def generate_random_email():
    timestamp = 6352340027
    return f"expensifyapp97+{timestamp}@gmail.com"


def login_user(p: PlaywrightContextManager, first_name="John", last_name="Doe") -> tuple[Browser, Page, str]:
    # Launch chromiun and open new page
    browser = p.chromium.launch(
        channel="chrome",
        headless=True,
        args=[
            "--ignore-certificate-errors",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ],
        proxy={"server": "http://localhost:8080"},
        slow_mo=500
    )
    page = browser.new_page()
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
    expect(page.locator("text=What do you want to do today?")).to_be_visible()

    # Step 4: Select 'Track and budget expenses' in onobarding page and click Continue

    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()
    page.wait_for_timeout(1000)

    # Step 5: Enter first name, last name and click continue
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()
    page.wait_for_timeout(1000)

    return browser, page, first_name, user_email


def test():
    with sync_playwright() as p:
        # Step 1: Login user
        browser, page, first_name, user_email = login_user(p)

        # Click second chat
        second_chat_button = page.locator(
            '[aria-label="Navigates to a chat"]').nth(1)

        second_chat_button.click()
        page.wait_for_timeout(1000)

        # Click Create button
        click_create_button = page.locator('button[aria-label="Create"]').last
        click_create_button.click()
        page.wait_for_timeout(1000)

        # Click assign task
        click_submit_expense_button = page.locator(
            "[aria-label='Assign task']")
        click_submit_expense_button.click()
        page.wait_for_timeout(1000)

        # fill title
        page.locator('input[aria-label="Title"]').fill("title something")
        page.wait_for_timeout(1000)

        # submit button
        button = page.locator('button', has_text="Next")
        button.click()
        page.wait_for_timeout(1000)

        # Locate the last div with role="menuitem"
        last_menuitem_div = page.locator('div[role="menuitem"]').nth(2)
        last_menuitem_div.click()
        page.wait_for_timeout(1000)

        # check for the text
        text = page.locator('div', has_text="Assign to me").nth(-1)
        expect(text).to_be_visible()
        page.wait_for_timeout(1000)

        browser.close()
