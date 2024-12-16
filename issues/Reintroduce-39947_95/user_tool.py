import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import re
import time
from playwright.sync_api import Playwright, Browser, Page, sync_playwright, expect
from utils.trace_cleaner import trace_cleaner

# Utility to generate a random email
def generate_random_email():
    timestamp = 64527005043
    return f"rgulraiz2000+{timestamp}@gmail.com"

def login_user(p: Playwright, first_name="D", last_name="C") -> tuple[Browser, Page, str]:
    # Launch chromium and open new page
    browser = p.chromium.launch(
        channel="chrome",
        headless=True,
        args=[
            "--ignore-certificate-errors",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ],
        proxy={"server": "http://localhost:8080"},
        slow_mo=1000
    )
    page = browser.new_page(viewport={"width": 1280, "height": 680})
    user_email = generate_random_email()

    # Step 1: Open expensify url
    page.goto('https://dev.new.expensify.com:8082/')

    # Step 2: Enter email and click continue
    page.get_by_test_id("username").fill(user_email)
    page.get_by_role("button", name="Continue").click()

    # Step 3: Click join button
    page.get_by_role("button", name="Join").click()
    expect(page.locator("text=What do you want to do today?")).to_be_visible(timeout=30000)

    # Step 4: Select 'Track and budget expenses' in onboarding page and click Continue
    page.locator("text='Track and budget expenses'").click()

    # Step 5: Enter first name, last name and click continue
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()

    return browser, page, user_email

def navigate_to_bank_account(page: Page):
    page.get_by_label("Start chat (Floating action)").click()
    page.get_by_label("New workspace").click()
    page.get_by_label("More features").click()
    page.get_by_label("Configure how spend is").click()
    page.get_by_label("Workflows").click()
    page.get_by_label("Connect bank account").click()

def disable_and_enable_payments(page: Page):
    page.wait_for_timeout(1000)
    btn = page.get_by_label("Add an authorized payer for")
    btn.click()
    page.wait_for_timeout(1000)
    btn.click()

def test_navigating():
    with sync_playwright() as playwright:
        browser, page, user_email = login_user(playwright)
        context = page.context
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        try:
            # Step 2: Navigate to bank account section
            navigate_to_bank_account(page)

            # Step 3: Go back and disable & enable payments
            page.get_by_role("button", name="Update to USD").click()
            page.get_by_test_id("BankAccountStep").get_by_label("Back").click()
            disable_and_enable_payments(page)

            # Step 4: Verify connect bank account button
            expect(page.get_by_label("Connect bank account")).to_be_visible()
        finally:
            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            browser.close()
