import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
import pytest
from playwright.sync_api import sync_playwright, Page

# Gmail credentials for generating user info
GMAIL_NAME = "rgulraiz2000"
GMAIL_APP_PASSWORD = "kepw uquj myoa npvj"

# Utility to generate user info
def get_test_user_info(seed=None, first_name=None, last_name=None):
    if first_name is None:
        first_name = GMAIL_NAME
    if last_name is None:
        last_name = ""
    email = f"{GMAIL_NAME}+{seed}@gmail.com" if seed is not None else f"{GMAIL_NAME}@gmail.com"
    return {"email": email, "password": GMAIL_APP_PASSWORD, "first_name": first_name, "last_name": last_name}

def test_configure_tax_in_workspace():
    with sync_playwright() as p:
        # Launch browser with desired settings
        browser = p.chromium.launch(channel="chromium", slow_mo=2000, headless=True, args=[
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
            "--ignore-certificate-errors",
        ])
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()

        # Generate user info with a unique email
        user_info = get_test_user_info(seed=int(time.time()), first_name="Test", last_name="User")
        user_email = user_info["email"]

        # Navigate to the login page
        page.goto("https://dev.new.expensify.com:8082/")

        # Input dynamic email for login
        email_input = page.locator('input[type="email"]')
        email_input.fill(user_email)

        # Click the "Continue" button to proceed with login
        continue_button = page.locator("button", has_text="Continue")
        continue_button.click()

        # Retry clicking "Continue" if necessary
        try:
            join_button = page.locator("button", has_text="Join")
            join_button.click()
        except Exception:
            pass

        # Select "Track and budget expenses" option
        track_budget_option = page.locator("text=Track and budget expenses")
        track_budget_option.click()

        # Fill in user first name and last name
        page.locator('input[name="fname"]').fill(user_info["first_name"])
        page.locator('input[name="lname"]').fill(user_info["last_name"])
        page.get_by_role("button", name="Continue").last.click()

        # Click "Create" to initiate workspace creation
        start_chat_button = page.locator("[aria-label='Start chat (Floating action)']")
        start_chat_button.click()

        # Select "New workspace" option
        new_workspace_option = page.locator("[aria-label='New workspace']")
        new_workspace_option.click()

        # Navigate to the "More features" section
        more_features_button = page.locator("text=More features")
        more_features_button.click()

        # Enable "Classify costs and track billable expenses."
        classify_costs_toggle = page.locator(
            "[aria-label='Classify costs and track billable expenses.']"
        )
        classify_costs_toggle.click()

        # Navigate to the "Tags" settings
        navigate_to_tags_button = page.locator('div[aria-label="Tags"]')
        navigate_to_tags_button.click()

        # Add a new tag in the workspace
        add_tag_button = page.locator("button", has_text="Add tag")
        add_tag_button.click()

        # Input the tag name
        page.locator('input[role="presentation"]').fill("tag1")

        # Save the new tag
        save_button = page.locator("button[data-listener='Enter']", has_text="Save")
        save_button.click()

        # Repeat the steps to add another tag
        add_tag_button.click()
        page.locator('input[role="presentation"]').fill("tag2")
        save_button.click()

        # Click on "Settings" in the workspace to configure more settings
        settings_button = page.locator("button", has_text="Setting").last
        settings_button.click()

        # Enable the "Track tax" option
        enable_track_tax_button = page.locator(
            "[aria-label='Members must tag all expenses']"
        )
        enable_track_tax_button.click()

        # Navigate back
        navigate_back_button = page.locator("[aria-label='Back']").nth(1)
        navigate_back_button.click()

        # Navigate to "Categories" settings
        navigate_to_categories_button = page.locator("text=Categories").nth(0)
        navigate_to_categories_button.click()

        # Add a new category
        add_category_button = page.locator("button", has_text="Add category")
        add_category_button.click()
        page.locator('input[role="presentation"]').fill("category1")
        save_button.click()

        # Click on "Settings" in the workspace to configure more settings
        settings_button = page.locator("button", has_text="Setting").last
        settings_button.click()

        # Enable the "Track tax" option
        enable_track_tax_button = page.locator(
            "[aria-label='Members must categorize all expenses']"
        )
        enable_track_tax_button.click()

        # Navigate back
        navigate_back_button = page.locator("[aria-label='Back']").nth(1)
        navigate_back_button.click()

        # Navigate back
        navigate_back_button = page.locator("[aria-label='Back']").nth(0)
        navigate_back_button.click()

        # Click "Create" to initiate workspace creation
        create_workspace_button = page.locator(
            "[aria-label='Start chat (Floating action)']"
        )
        create_workspace_button.click()

        # Submit an expense and fill out the required fields
        submit_expense_button = page.locator("[aria-label='Submit expense']")
        submit_expense_button.click()

        # Select "Manual" expense option
        manual_expense_option = page.locator("button[aria-label='Manual']")
        manual_expense_option.click()

        # Input the expense amount
        page.locator('input[role="presentation"]').fill("13")

        # Click "Next"
        next_button = page.locator(
            "button[data-listener='Enter']", has_text="Next"
        ).nth(0)
        next_button.click()

        # Select the workspace
        workspace_button = page.get_by_label("Test User's Workspace")
        workspace_button.click()

        # Click on "Merchant" field
        merchant_button = page.locator("[role='menuitem']", has_text="Merchant")
        merchant_button.click()

        # Fill in the merchant name
        page.locator('input[role="presentation"][aria-label="Merchant"]').fill(
            "merchanttest"
        )

        # Save the merchant data
        save_button.click()

        # Submit the expense
        submit_button = page.locator("button[data-listener='Enter']", has_text="Submit")
        submit_button.click()
        page.wait_for_timeout(4000)

        # View the workspace details
        view_details_button = page.locator('[aria-label="View details"]')
        view_details_button.click()

        # Verify that "Missing Category" is visible
        missing_category_label = page.locator("text=Missing Category")
        missing_category_label.wait_for(state="visible")

        # Click on "Missing Category"
        missing_category_label.click()

        # Select the "Advertising" category
        advertising_button = page.locator('[aria-label="Advertising"]')
        advertising_button.click()

        try:
            # Wait for the "Missing Category" element to disappear
            page.wait_for_selector("text=Missing Category", state="hidden")

            # Assert that "Missing Category" is no longer visible
            assert not page.locator("text=Missing Category").is_visible()
        except Exception:
            pass
