import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page

from utils.trace_cleaner import trace_cleaner

# Utility to generate a random email
def generate_random_email():
    return "asdasdas+84894@gmail.com"


def login_user(p: PlaywrightContextManager, first_name="Ayush", last_name="G") -> tuple[Browser, Page, str]:
    # Launch chromium and open new page
    browser = p.chromium.launch(channel="chrome", headless=True, slow_mo=1000, args=[
        "--ignore-certificate-errors",
        "--disable-web-security",
        "--disable-features=IsolateOrigins,site-per-process"
    ])
    page = browser.new_page()
    user_email = generate_random_email()

    # Step 1: Open expensify url
    page.goto('https://dev.new.expensify.com:8082/')

    # Step 2: Enter email and click continue
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()

    # Step 3: Click join button
    try:
        page.locator('button[tabindex="0"]').click()
    except Exception:
        pass

    expect(page.locator("text=What do you want to do today?")).to_be_visible()

    # Step 4: Select 'Track and budget expenses' in onboarding page and click Continue
    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()

    # Step 5: Enter first name, last name and click continue
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()

    return browser, page, user_email


def test_save_description_in_submitted_expense():
    with sync_playwright() as p:
        browser, page, user_email = None, None, None
        context = None
        try:
            # Step 1: Login user
            browser, page, user_email = login_user(p)

            # Obtain the context from the page
            context = page.context
            # Start tracing
            context.tracing.start(screenshots=True, snapshots=True, sources=True)

            # Remaining test steps
            page.locator('span:text("Ayush G (you)")').click()

            plus_create_icon = page.locator('button[aria-label="Create"]').last
            expect(plus_create_icon).to_be_visible()
            plus_create_icon.click()

            page.get_by_text("Assign task").click()
            page.get_by_role("textbox", name="Title").fill("sample title")
            page.get_by_role("textbox", name="Title").press("Tab")
            page.get_by_role("textbox", name="Description (optional)").fill("sample description")
            page.get_by_role("button", name="Next").click()

            page.locator('button div:text("Confirm task")').click()

            task_title_div = page.locator('div[data-testid="comment"] div:has-text("sample title")')
            task_title_div.click()

            expanded_task_title_div = page.locator('div[aria-label="sample title"]').first
            expanded_task_title_div.click()

            page.get_by_role("textbox", name="Title").fill("")
            page.get_by_role("button", name="Save").click()

            title_missing_warning = page.locator('div:text("Please enter a title")')
            expect(title_missing_warning).to_be_visible()

            field_required_warning = page.locator('div:text("This field is required.")')
            expect(field_required_warning).to_be_hidden()

        except Exception as e:
            # Re-raise the exception so the test fails if needed
            raise e
        finally:
            # Stop tracing and clean the trace
            if context:
                context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
                trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            if browser:
                browser.close()
