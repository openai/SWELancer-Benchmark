import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page

from utils.trace_cleaner import trace_cleaner

# Utility to generate a random email for testing
def generate_random_email():
    return "expensify624+1734169909@gmail.com"


def login_user(
    p: PlaywrightContextManager, first_name="A", last_name="Khan"
) -> tuple[Browser, Page, str]:
    # Launch Chromium browser and open a new page
    browser = p.chromium.launch(
        channel="chrome",
        headless=True,
        args=[
            "--ignore-certificate-errors",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
        ],
        proxy={"server": "http://localhost:8080"},
        slow_mo=500,
    )
    page = browser.new_page()
    context = browser.new_context()
    user_email = generate_random_email()

    # Open the Expensify URL
    page.goto("https://dev.new.expensify.com:8082/")

    # Enter the generated email and click continue
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()

    # Click the join button if necessary (in case it didn't register the first time)
    try:
        page.locator('button[tabindex="0"]').click()

    except Exception:
        pass

    # Ensure that the user has reached the main menu
    expect(page.locator("text=What do you want to do today?")).to_be_visible()

    # Select 'Track and budget expenses' during onboarding and click Continue
    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()

    # Enter first name and last name, then click continue
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()

    return browser, page, context


def test_exit_survey_confirmation_page():
    with sync_playwright() as p:
        browser, page, context = login_user(p)

        # Start Playwright trace recording
        context.tracing.start(screenshots=True, snapshots=True, sources=True)

        try:
            # Navigate to exit-survey reason page
            page.goto("https://dev.new.expensify.com:8082/settings/exit-survey/reason ")

            # Check one of the box
            page.get_by_text("I don't understand how to use New Expensify.").click()
            # Click on next button
            page.get_by_text("Next").click()
            # Fill in the textbox
            page.get_by_role("textbox", name="Your response").fill("N/A")
            # Click on next button
            page.get_by_role("button", name="Next").click()
            # Click on Switch to Expensify Classic button
            page.get_by_role("button", name="Switch to Expensify Classic").click()

            # Verify the modal is not visible
            expect(page.get_by_test_id("ExitSurveyConfirmPage")).not_to_be_visible()
        except Exception as e:
            # Stop and save the trace even if the test fails
            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            raise e
        else:
            # Stop and save the trace if the test passes
            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
        finally:
            # Close the browser in any case
            browser.close()
