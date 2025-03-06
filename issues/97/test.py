import re
import os
import time
import numpy as np
from PIL import Image
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
    page.get_by_test_id("WorkspacePageWithSections").get_by_text("Name").click()
    page.get_by_role("textbox", name="Name").press("ControlOrMeta+a")
    page.get_by_role("textbox", name="Name").fill("Test Workspace")
    page.get_by_role("button", name="Save").click()
    page.get_by_test_id("WorkspaceInitialPage").get_by_label("Back").click()


def test_workspace_options_and_button_color():
    with sync_playwright() as pw:
        
        email_address = "biruktassew21+1739868840535192@gmail.com"

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
    
        # signup user
        signup_user(page, email_address)

        # Create workspace
        create_workspace(page)

        expected_color = "rgb(230, 225, 218)"
        create_workspace_button = page.get_by_label("New workspace")
        actual_color = create_workspace_button.evaluate("button => getComputedStyle(button).backgroundColor")
        page.get_by_label("More").first.click()
        
        # Assert the color matches the expected standard
        expect(page.get_by_text("Go to workspace")).to_be_visible()
        assert actual_color == expected_color, f"Expected {expected_color}, but got {actual_color}"
        

        # Close the browser
        browser.close()

