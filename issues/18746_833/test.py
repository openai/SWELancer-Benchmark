import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page
import platform  


# Utility to generate a random email
def generate_random_email():
    return "testerbro7077+462468@gmail.com"


def login_user(p: PlaywrightContextManager, first_name="John", last_name="Doe") -> tuple[Browser, Page, str]:
    # Launch chromiun and open new page
    browser = p.chromium.launch(channel="chrome", headless=True, slow_mo=500, args=[
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
            ])
    page = browser.new_page()
    user_email = generate_random_email()

    # Step 1: Open expensify url
    page.goto('https://dev.new.expensify.com:8082/')

    # Step 2: Enter email and click continue
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(2000)

    # Step 3: Click join button
    try:
        page.locator('button[tabindex="0"]').click()
        page.wait_for_timeout(2000)
    except Exception:
        pass
    expect(page.locator("text=What do you want to do today?")).to_be_visible()

    # Step 4: Select 'Track and budget expenses' in onobarding page and click Continue

    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()
    page.wait_for_timeout(2000)

    # Step 5: Enter first name, last name and click continue
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()
    page.wait_for_timeout(2000)

    return browser, page, first_name, last_name


def test():
    with sync_playwright() as p:
        # Step 1: Login user
        browser, page, first_name, last_name = login_user(p)

        page.wait_for_timeout(2000)

        # Click your WS
        click_WS = page.locator(
            "div", has_text=f"{first_name} {last_name} (you)").nth(-1)
        click_WS.click()
        page.wait_for_timeout(2000)

        # input text in chat
        input_text_in_chat = page.locator('div[role="textbox"]').nth(-1)
        input_text_in_chat.fill("@h")
        page.wait_for_timeout(2000)

        # test the @here
        text_here = page.locator('div', has_text="@here").nth(-1)
        expect(text_here).to_be_visible()
        page.wait_for_timeout(2000)

        browser.close()