import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import re
import time
from playwright.sync_api import sync_playwright
from utils.trace_cleaner import trace_cleaner

# Constants for URLs and credentials
NEWDOT_URL = "https://dev.new.expensify.com:8082/"
EMAIL = "checkissue96+26002@gmail.com"


def login_user(p):
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
        slow_mo = 1000
    )

    context_args = {
        "timezone_id": "America/Los_Angeles",
    }

    context = browser.new_context(**context_args)
    page = context.new_page()

    user_email = EMAIL

    # Step 1: Open expensify url
    page.goto('https://dev.new.expensify.com:8082/')

    page.locator('input[type="email"]').fill(user_email)
    page.get_by_role("button", name="Continue").nth(0).click()
    
    page.get_by_role("button", name="Join").click()

    # Update profile
    page.get_by_text("Track and budget expenses").click()

    page.get_by_role("textbox", name="First name").fill("Test")

    page.get_by_role("textbox", name="Last name").fill("User")
    
    page.get_by_role("button", name="Continue").click()

    return browser, page


def test():
    with sync_playwright() as p:
        trace_path = "/app/expensify/user_tool/output_browser1.zip"
        browser, page = login_user(p)
        context = page.context

        # Start Playwright tracing
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        try:
            # Click settings
            click_settings_button = page.locator("[aria-label='My settings']")
            click_settings_button.click()

            # Click workspaces
            click_workspace_button = page.locator("div[aria-label='Workspaces']")
            click_workspace_button.click()

            # Create new workspaces
            create_new_workspace_button = page.locator("[aria-label='New workspace']").nth(0)
            create_new_workspace_button.click()

            workspace_name_div = page.locator('//div[contains(text(), "Name")]/following-sibling::div[1]/div')
            workspace_name = workspace_name_div.text_content(timeout=15000)

            # Click Back button
            click_back_button = page.locator("[aria-label='Back']").last
            click_back_button.click()

            # Click Inbox
            click_Inbox = page.locator("button[aria-label='Inbox']").last
            click_Inbox.click()

            # Click WS chat
            target_inbox_item = page.locator('//button[@aria-label="Navigates to a chat" or @aria-label="Navega a un chat"]', has_text=workspace_name)
            target_inbox_item.click()

            # Edit input text
            edit_input_text = page.locator('div[contenteditable="true"]').last

            # Focus on the div by clicking it
            edit_input_text.fill("hiiii I am here")

            # send the message
            send_message = page.locator("[aria-label='Send']")
            send_message.click()

            # hover the sent message
            hover_message = page.locator('div[aria-label="Chat message"]', has_text="hiiii I am here").last
            hover_message.hover()

            # click reply in thread
            click_reply_in_thread = page.locator('button[aria-label="Reply in thread"]').last
            click_reply_in_thread.click()

            # Click reply in thread
            logos_reply_chat = page.locator('button[aria-label="hiiii I am here"]').last

            # Get the first child div inside the button
            button_content = logos_reply_chat.locator("div").nth(0)

            # Locate only the direct child divs (first-level children)
            # Use `:scope` to limit to direct children
            outer_divs = button_content.locator(":scope > div").all()

            # Assert that there are exactly two outer divs
            assert len(outer_divs) == 2, f"Expected 2 outer divs, but found {len(outer_divs)}"

            # Hover over the first two outer divs
            for i, child in enumerate(outer_divs[:2]):
                child.hover(timeout=1000)
        finally:
            # Stop tracing and clean up the trace, even on failure
            context.tracing.stop(path=trace_path)
            trace_cleaner(trace_path)
            browser.close()
