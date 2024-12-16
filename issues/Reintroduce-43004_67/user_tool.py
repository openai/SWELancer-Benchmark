import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import re
from email.header import decode_header
from playwright.sync_api import sync_playwright, expect
from utils.trace_cleaner import trace_cleaner

def login_user(page) -> None:
    # Step 1: Enter email and click continue
    username_input = page.get_by_test_id("username")
    username_input.click()
    username_input.fill("rgulraiz2000+709080968@gmail.com")
    continue_button = page.get_by_role("button", name="Continue")
    continue_button.click()
    page.wait_for_timeout(2000)

    # Step 2: Click join button
    join_button = page.get_by_role("button", name="Join")
    join_button.click()
    page.wait_for_timeout(2000)

    # Step 3: Select 'Track and budget expenses' in onboarding page and click Continue
    track_expenses_text = page.get_by_text("Track and budget expenses")
    track_expenses_text.click()
    page.wait_for_timeout(1000)

    # Step 3: Enter first name, last name and click continue
    first_name_input = page.get_by_role("textbox", name="First name")
    first_name_input.fill('Yagan')
    first_name_input.press("Tab")
    last_name_input = page.get_by_role("textbox", name="Last name")
    last_name_input.fill('Sai')

    # Step 4: Click continue button
    continue_button_after_names = page.get_by_role("button", name="Continue")
    continue_button_after_names.click()
    page.wait_for_timeout(1000)


def check_error_page(page):
    # Create a new workspace
    page.get_by_label("Workspaces").click()
    page.get_by_role("button", name="Get Started").click()
    page.get_by_label("Back").click()
    page.get_by_label("Inbox").click()

    # Submit an expense
    page.locator('button[aria-label="Navigates to a chat"]').nth(2).click()
    page.get_by_label("Create").nth(1).click()
    page.wait_for_timeout(1000)
    page.get_by_text("Submit expense", exact=True).click()
    page.wait_for_timeout(1000)
    page.get_by_label("Manual").click()
    page.wait_for_timeout(1000)
    page.get_by_placeholder("0").fill("100")
    page.locator("#numPadContainerView").get_by_role("button", name="Next").click()
    page.get_by_text("Merchant").click()
    page.wait_for_timeout(1000)
    page.get_by_role("textbox", name="Merchant").fill("Test")
    page.get_by_role("button", name="Save").click()
    page.get_by_role("button", name=re.compile(r"Submit [\w$€£¥]+")).click()

    # Open the Expense report
    page.get_by_role("button", name="View details").nth(0).click()
    page.wait_for_timeout(1000)
    current_url = page.url
    last_numeric_value = current_url.split('/')[-1]
    print(f"Last numeric value: {last_numeric_value}")
    page.wait_for_timeout(1000)

    # Locally merge incorrect currency data
    page.evaluate(f'Onyx.merge("report_{last_numeric_value}",{{"currency": null}})')
    error_message = page.locator("div.css-text-146c3p1", has_text="Uh-oh, something went wrong!")
    if error_message.is_visible():
        sign_out_button = page.locator("button.css-view-175oi2r", has_text="Sign out")
        sign_out_button.click()
        raise AssertionError("Error message 'Uh-oh, something went wrong!' is visible")
    else:
        assert True


def test_login():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="chrome",
            headless=True,
            args=[
                "--ignore-certificate-errors",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process"
            ],
            proxy={"server": "http://localhost:8080"},
            slow_mo=500
        )

        context = browser.new_context()
        context.tracing.start(screenshots=True, snapshots=True, sources=True)

        try:
            page = context.new_page()
            page.goto("https://dev.new.expensify.com:8082/")
            page.wait_for_timeout(2000)

            # Step 1: Login user
            login_user(page)
            check_error_page(page)
            page.close()
        except Exception as e:
            raise e
        finally:
            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            context.tracing.stop(path=trace_path)
            trace_cleaner(trace_path)
            context.close()
            browser.close()
