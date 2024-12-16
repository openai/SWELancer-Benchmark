import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page
from utils.trace_cleaner import trace_cleaner


def generate_random_email():
    timestamp = int(time.time())
    return f"milan.thummar7476848@gmail.com"


def login_user(p: PlaywrightContextManager, first_name="Milan", last_name="T") -> tuple[Browser, Page, str]:
    # Launch chromium and open new page
    browser = p.chromium.launch(headless=True, args=[
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
        ],
    )
    # Create a context so that we can start tracing within it
    context = browser.new_context()
    page = context.new_page()
    user_email = generate_random_email()

    # Step 1: Open expensify url
    page.goto('https://dev.new.expensify.com:8082/')

    # Step 2: Enter email and click continue
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(1000)

    # Step 3: Click join button
    try:
        page.locator('button[tabindex="0"]').click()
        page.wait_for_timeout(1000)
    except Exception:
        pass
    try:
        expect(page.locator("text=What do you want to do today?")).to_be_visible()
        
        # Step 4: Select 'Track and budget expenses' in onboarding page and click Continue
        page.locator("text='Track and budget expenses'").click()
        page.get_by_role("button", name="Continue").click()
        page.wait_for_timeout(1000)

        # Step 5: Enter first name, last name and click continue
        page.locator('input[name="fname"]').fill(first_name)
        page.locator('input[name="lname"]').fill(last_name)
        page.get_by_role("button", name="Continue").last.click()
    except:
        pass
    page.wait_for_timeout(1000)

    return browser, page, user_email


def enable_report_fields(
    browser: Browser, 
    page: Page, 
    user_email: str, 
):
    # Click on more features
    more_features_button = page.locator('div[aria-label="More features"]')
    expect(more_features_button).to_be_visible()
    page.wait_for_timeout(1000)
    more_features_button.click()
    page.wait_for_timeout(1000)

    report_fields_button = page.locator('div[aria-label="Report fields"][role="menuitem"]')
    if not report_fields_button.is_visible():
        # Enable report fields
        report_fields_switch = page.locator('button[aria-label="Set up custom fields for spend."]')
        expect(report_fields_switch).to_be_visible()
        page.wait_for_timeout(1000)
        report_fields_switch.click()
        page.wait_for_timeout(1000)
    
    try:
        page.locator('button[data-tag="pressable"]', has_text="Upgrade").last.click()
        page.wait_for_timeout(1000)

        page.locator('button[data-tag="pressable"]', has_text="Got it, thanks").last.click()
        page.wait_for_timeout(1000)
    except Exception:
        pass

    page.wait_for_timeout(1000)
    expect(report_fields_button).to_be_visible()
    page.wait_for_timeout(1000)
    report_fields_button.click()
    page.wait_for_timeout(1000)

    return browser, page, user_email


def create_new_workspace(
    browser: Browser, 
    page: Page, 
    user_email: str, 
) -> tuple[Browser, Page, str]:
    # Step 1: Click on + icon and click on "New workspace"
    plus_icon = page.locator('button[aria-label="Start chat (Floating action)"]')
    expect(plus_icon).to_be_visible()
    plus_icon.click()
    page.wait_for_timeout(1000)

    new_workspace_button = page.locator('div[aria-label="New workspace"]')
    expect(new_workspace_button).to_be_visible()
    new_workspace_button.click()
    page.wait_for_timeout(1000)

    return browser, page, user_email


def add_report_field_list_value(
    page: Page, 
    value: str, 
) -> Page:
    page.locator('button', has_text="Add value").last.click()
    page.wait_for_timeout(1000)
    
    page.locator('input[aria-label="Value"]').last.fill(value)
    page.wait_for_timeout(1000)

    page.locator('button[data-listener="Enter"]', has_text="Save").last.click()
    page.wait_for_timeout(1000)

    return page


def test_report_fields_not_visible_after_desabling_feature():
    with sync_playwright() as p:
        # Step 1: Login user
        browser, page, user_email = login_user(p)

        # Start tracing
        page.context.tracing.start(screenshots=True, snapshots=True)
        try:
            # Step 2: Create a new workspace and enable report fields
            browser, page, user_email = create_new_workspace(browser, page, user_email)
            browser, page, user_email = enable_report_fields(browser, page, user_email)

            # Step 3: Add list field
            page.locator('button', has_text="Add field").last.click()
            page.wait_for_timeout(1000)

            page.locator('div[role="menuitem"]', has_text="Name").last.click()
            page.wait_for_timeout(1000)

            page.locator('input[aria-label="Name"]').last.fill("MyListReportField")
            page.wait_for_timeout(1000)

            page.locator('button[data-listener="Enter"]', has_text="Save").last.click()
            page.wait_for_timeout(1000)

            page.locator('div[role="menuitem"]', has_text="Type").last.click()
            page.wait_for_timeout(1000)

            page.locator('button[aria-label="List"]', has_text="List").last.click()
            page.wait_for_timeout(1000)

            # Step 4: Create list values
            page.locator('div[role="menuitem"][tabindex="0"]', has_text="List values").last.click()
            page.wait_for_timeout(1000)

            page = add_report_field_list_value(page, "TestValueA")
            page = add_report_field_list_value(page, "TestValueB")
            page = add_report_field_list_value(page, "TestValueC")

            page.locator('button[aria-label="Back"]').last.click()
            page.wait_for_timeout(1000)

            # Step 5: Validate initial values menuitem is visible below the list values
            list_values_menuitem = page.locator('div[role="menuitem"][tabindex="0"]', has_text="List values").last
            expect(list_values_menuitem).to_be_visible()
            list_values_bounding_box = list_values_menuitem.bounding_box()

            initial_values_menuitem = page.locator('div[role="menuitem"][tabindex="0"]', has_text="Initial value").last
            expect(initial_values_menuitem).to_be_visible()
            initial_values_bounding_box = initial_values_menuitem.bounding_box()

            assert list_values_bounding_box['y'] < initial_values_bounding_box['y']

            # Step 6: Validate created values are visible as comma separated list
            list_values = page.locator('div', has_text="TestValueA, TestValueB, TestValueC").last
            expect(list_values).to_be_visible()
            page.wait_for_timeout(2000)
        except Exception as e:
            print(f"Test failed: {e}")
            raise e
        finally:
            # Stop tracing and clean trace even if test fails
            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            page.context.tracing.stop(path=trace_path)
            trace_cleaner(trace_path)
            browser.close()
