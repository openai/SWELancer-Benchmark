import time
from playwright.sync_api import sync_playwright, expect

# Expensify app URL
NEWDOT_URL = "https://dev.new.expensify.com:8082"
OLDDOT_URL = "http://127.0.0.1:9000/"
GMAIL = "biruktassew21@gmail.com"

def generate_new_email(email_address=GMAIL):
        # Add random number suffix to the email before the "@" symbol
        username, domain = email_address.split('@')
        timestamp = int(time.time() * 1_000_000)
        return f"{username}+{timestamp}@{domain}"

def test_workspace_count():
    with sync_playwright() as pw:
        
        email_address = "biruktassew21+1739891868933537@gmail.com"

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
        
        page = browser.new_page()
        page.goto(NEWDOT_URL)

        # Sign up
        page.get_by_test_id("username").click()
        page.get_by_test_id("username").fill(email_address)
        page.get_by_role("button", name="Continue").click()
        page.get_by_role("button", name="Join").click()

        # Fill out the onboarding form
        page.get_by_text("Manage my team's expenses").click()
        page.get_by_label("-10 employees").click()
        page.get_by_role("button", name="Continue").click()
        page.get_by_test_id("BaseOnboardingAccounting").get_by_label("Back").click()
        page.get_by_label("-50 employees").click()
        page.get_by_role("button", name="Continue").click()
        page.get_by_label("None of the above").click()
        page.get_by_role("button", name="Continue").click()

        # Verify the number of workspaces created
        page.get_by_label("My settings").click()
        page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").get_by_text("Workspaces").click()
        workspace = page.get_by_label("row")

        # Assert the number of workspaces created is not greater than one
        expect(workspace).to_have_count(1)

        # Close the browser
        browser.close()

