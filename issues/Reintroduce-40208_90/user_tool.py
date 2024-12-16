import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import pytest
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page

from utils.trace_cleaner import trace_cleaner

# Utility to generate a random email
def generate_random_email() -> str:
    return 't1533148+1734073036@gmail.com'

# Function to login a user
def signup_user(page, user_email, first_name, last_name) -> tuple[Page, str, str, str]:
    page.goto('https://127.0.0.1:8082/')
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()

    try:
        page.get_by_role("button", name="Join").click()
        
        page.locator("text='Manage my team's expenses'").click()
        page.get_by_role("button", name="Continue").click()
        
        page.locator('input[name="fwork"]').fill("Turingg")
        page.get_by_role("button", name="Continue").last.click()
        
        page.locator('input[name="fname"]').fill(first_name)
        page.locator('input[name="lname"]').fill(last_name)
        page.get_by_role("button", name="Continue").last.click()
    except Exception:
        pass

# Function to check pause functionality and play uploaded video
def run_test(page: Page) -> None:
    my_settings = page.locator('button[aria-label="My settings"]')
    expect(my_settings).to_be_visible()
    my_settings.click()

    work_spaces = page.locator('div[aria-label="Troubleshoot"]')
    expect(work_spaces).to_be_visible()
    work_spaces.click()

    client = page.locator('button[aria-label="Client side logging"]')
    expect(client).to_be_visible()
    client.click()

    client1 = page.locator('button[aria-label="Client side logging"]')
    expect(client1).to_be_visible()
    client1.click()

    share = page.locator('button:has-text("Share")').nth(-1)
    expect(share).to_be_visible()
    share.click()

@pytest.mark.parametrize("first_name, last_name", [("AK", "Test")])
def test_expensify(first_name: str, last_name: str) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            channel="chrome", headless=True,
            args=["--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"],
            slow_mo=1000
        )
        context_args = {}
        context_args["geolocation"] = {"latitude": 37.7749, "longitude": 122.4194}
        context_args["permissions"] = ["geolocation"]
        context_args["ignore_https_errors"] = True
        context = browser.new_context(**context_args)
        page = context.new_page()

        # Start tracing
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        try:
            user_email = generate_random_email()
            signup_user(page, user_email, first_name, last_name)
            run_test(page)
        except Exception as e:
            # We re-raise after ensuring the trace will be saved
            raise e
        finally:
            # Stop tracing and save
            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            context.tracing.stop(path=trace_path)
            trace_cleaner(trace_path)

        browser.close()

if __name__ == "__main__":
    pytest.main([__file__])
