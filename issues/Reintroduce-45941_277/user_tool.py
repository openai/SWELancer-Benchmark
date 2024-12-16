import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from utils.trace_cleaner import trace_cleaner  # <--- Added import


# Utility to generate a random email for testing
def generate_random_email():
    timestamp = int(time.time())
    return f"expensify624+{timestamp}@gmail.com"

# USER_EMAIL = generate_random_email()
USER_EMAIL = "expensify624+348@gmail.com"


def login_user(p: PlaywrightContextManager, first_name="A", last_name="Khan") -> tuple[Browser, Page, str]:
    # Launch chromium browser and open a new page
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
    page = context.new_page()

    # Step 1: Open the Expensify URL
    page.goto('https://dev.new.expensify.com:8082/')

    # Step 2: Enter the generated email and click continue
    page.locator('input[type="email"]').fill(USER_EMAIL)
    page.locator('button[tabindex="0"]').click()
    time.sleep(1)

    # Step 3: Click the join button if necessary (in case it didn't register the first time)
    try:
        page.locator('button[tabindex="0"]').click()
        time.sleep(1)
    except Exception:
        pass

    # Step 4: Ensure that the user has reached the main menu
    expect(page.locator("text=What do you want to do today?")).to_be_visible()

    # Step 5: Select 'Track and budget expenses' during onboarding and click Continue
    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()
    time.sleep(1)

    # Step 6: Enter first name and last name, then click continue
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()
    time.sleep(1)

    # Return the browser, page
    return browser, page, context


def test_old_dot_page_redirection():
    with sync_playwright() as p:
        # Start playwright tracing
        p.tracing.start(
            title="test_old_dot_page_redirection",
            screenshots=True,
            snapshots=True
        )

        try:
            browser, page, context = login_user(p)

            # Navigate to exit-survey reason page
            page.goto('https://dev.new.expensify.com:8082/settings/exit-survey/reason')
            time.sleep(1)

            # Assert that the exit survey page is opened
            expect(page).to_have_url('https://dev.new.expensify.com:8082/settings/exit-survey/reason')

            # Check one of the boxes and fill in the form
            page.get_by_text("I don't understand how to use New Expensify.").click()

            # Assert the correct option is selected
            expect(page.get_by_text("I don't understand how to use New Expensify.")).to_be_visible()

            # Click on the next button and proceed
            page.get_by_text("Next").click()

            # Fill in the response textbox
            page.get_by_role("textbox", name="Your response").fill("N/A")

            # Assert the textbox has the correct value
            expect(page.get_by_role("textbox", name="Your response")).to_have_value("N/A")

            # Click on the Next button
            page.get_by_role("button", name="Next").click()

            # Click on the "Switch to Expensify Classic" button
            page.get_by_role("button", name="Switch to Expensify Classic").click()

            try:
                # Expect the new page (new tab) to open
                with context.expect_page() as new_page_info:
                    new_page = new_page_info.value

                    # Assert that the new page was successfully opened
                    assert new_page is not None, "A new tab should have opened but it didn't."

            except PlaywrightTimeoutError:
                assert False, "Failed to open new tab after clicking the 'Switch to Expensify Classic' button."

            # Sleep to allow observation if needed
            time.sleep(1)

            # Close the browser
            browser.close()

        except Exception as e:
            # Reraise the exception so the test fails, but still proceed to finally block
            raise e

        finally:
            # Stop tracing and save the trace
            p.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            # Clean the trace
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
