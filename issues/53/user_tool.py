import re
import os
import time
import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright, expect
from utils.trace_cleaner import trace_cleaner

# Expensify app URL
NEWDOT_URL = "https://dev.new.expensify.com:8082"
OLDDOT_URL = "http://127.0.0.1:9000/"
GMAIL = "biruktassew21@gmail.com"

def generate_new_email(email_address=GMAIL):
    # Add random number suffix to the email before the "@" symbol
    username, domain = email_address.split('@')
    timestamp = int(time.time() * 1_000_000)
    return f"{username}+{timestamp}@{domain}"


def signup_user(page, email, first_name="Test", last_name="User"):
    page.get_by_role("textbox", name="Phone or email").fill(email)
    page.get_by_role("button", name="Continue").click()
    page.get_by_role("button", name="Join").click()

    page.wait_for_selector('text="What do you want to do today?"')
    expect(page.locator("text=What do you want to do today?")).to_be_visible()
    
    page.get_by_label("Track and budget expenses").click()
    page.get_by_role("button", name="Continue").click()

    page.fill('input[name="fname"]', first_name)
    page.fill('input[name="lname"]', last_name)
    page.get_by_role("button", name="Continue").last.click()

    page.wait_for_timeout(2000)


def create_workspace(page):
    # create a workspace and go to its chat
    page.get_by_label("My settings").click()
    page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").get_by_text("Workspaces").click()
    page.get_by_label("New workspace").first.click()


def test_horizontal_divider_visibility():
    with sync_playwright() as pw:
        email_address = 'biruktassew21+1739518540770268@gmail.com'

        # Launch the app
        browser = pw.chromium.launch(
            channel="chrome",
            headless=False,
            args=[
                "--ignore-certificate-errors",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process"
            ],
            proxy={"server": "http://localhost:8080"},
            slow_mo=500
        )

        # Create a new browser context and start tracing
        context = browser.new_context()
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        page = context.new_page()

        try:
            page.goto(NEWDOT_URL)
        
            # signup user
            signup_user(page, email_address)

            # Create workspace
            create_workspace(page)
            
            # Navigate to categories settings
            page.get_by_text("Categories").click()
            page.get_by_test_id("WorkspaceCategoriesPage").get_by_role("button", name="Settings").click()

            # Assert if the horizontal devider exist
            divider = page.locator("div[style*='height: 1px'][style*='background-color: rgb(230, 225, 218)'][style*='margin: 24px 20px']")
            expect(divider).to_be_visible()

        finally:
            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            context.tracing.stop(path=trace_path)
            trace_cleaner(trace_path)
            browser.close()


if __name__ == '__main__':
    test_horizontal_divider_visibility()