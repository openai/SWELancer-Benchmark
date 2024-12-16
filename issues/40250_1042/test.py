import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright

def test_offline_message_not_visible_when_online():
    with sync_playwright() as p:
        # Launch the browser
        browser = p.chromium.launch(headless=True, args=[
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
        ])
        page = browser.new_page()

        # Go to the app URL
        page.goto("https://dev.new.expensify.com:8082/")

        # Simulate being online
        page.context.set_offline(False)

        # Wait for the page to fully load the online state
        page.wait_for_timeout(2000)  # Add a short delay to ensure the page has updated its state

        # Check that the "You appear to be offline" message is NOT visible
        offline_message = page.locator("text=You appear to be offline")
        
        # Assert that the message is not visible when online
        assert offline_message.count() == 0, "The offline message should not be visible when online"

        # Close the browser
        browser.close()
