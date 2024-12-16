import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
import random
import re
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page
from utils.trace_cleaner import trace_cleaner

# Utility to generate a random email
def generate_random_email():
    return "redx224+6856@gmail.com"


def login_user(p: PlaywrightContextManager, first_name="Milan", last_name="T") -> tuple[Browser, Page, str]:
    # Launch chromium and create a browser context for tracing
    browser = p.chromium.launch(channel="chrome", headless=True, args=[
        "--disable-web-security",
        "--disable-features=IsolateOrigins,site-per-process"
    ])
    context = browser.new_context()

    # Start tracing to capture login steps
    context.tracing.start(screenshots=True, snapshots=True, sources=True)

    page = context.new_page()
    user_email = generate_random_email()

    # Step 1: Open expensify url
    page.goto('https://dev.new.expensify.com:8082/')

    # Step 2: Enter email and click continue
    page.locator('input[type="email"]').fill(user_email)
    page.get_by_role("button", name="Continue").click()

    # Step 3: Click join button
    page.get_by_role("button", name="Join").click()

    page.wait_for_selector("text=What do you want to do today?")
    expect(page.locator("text=What do you want to do today?")).to_be_visible()

    # Step 4: Select 'Track and budget expenses' in onboarding page and click Continue
    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()
    page.wait_for_timeout(500)

    # Step 5: Enter first name, last name and click continue
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()
    page.wait_for_timeout(500)

    # Return browser, the active page, and the email
    return browser, page, user_email


def test_issue_18909():
    with sync_playwright() as p:
        browser, page, user_email = login_user(p)
        # We'll retrieve the context from the page
        context = page.context
        try:
            own_chat = page.get_by_text("Milan T (you)")
            expect(own_chat).to_be_visible()
            own_chat.click()
            page.wait_for_timeout(500)

            emoji = page.locator('div[aria-label="Emoji"]').nth(1)
            expect(emoji).to_be_visible()
            emoji.click()
            page.wait_for_timeout(500)

            page.locator('input[aria-label="Search"]').nth(0).fill("avsfb")
            test = page.locator("div").filter(has_text=re.compile(r"^Search$")).first
            page.wait_for_timeout(500)
            expect(test).to_have_css("padding", "8px 16px 12px")
        except Exception as e:
            # Raise error again to indicate test failure, but only after we save the trace
            raise e
        finally:
            # Stop trace and clean it
            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            # Close the browser
            browser.close()
