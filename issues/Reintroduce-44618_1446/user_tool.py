import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page
from playwright._impl._browser_context import BrowserContext

from utils.trace_cleaner import trace_cleaner


def login_user(context: BrowserContext, first_name="A", last_name="Khan") -> tuple[Page, str]:
    # Open new page from the context
    page = context.new_page()
    user_email = "exxpp00112+11111@gmail.com"

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
    
    expect(page.locator("text=What do you want to do today?")).to_be_visible()

    # Step 4: Select 'Track and budget expenses' in onobarding page and click Continue
    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()
    page.wait_for_timeout(1000)


    # Step 5: Enter first name, last name and click continue
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()
    page.wait_for_timeout(1000)

    return page, user_email


def set_default_currency(page: Page, currency: str) -> Page:
    # Step 1: Open the 'Default currency' menu item
    default_currency_button = page.locator('div[role="menuitem"]').get_by_text("Default currency")
    expect(default_currency_button).to_be_visible()
    default_currency_button.click()

    # Step 2: Fill in the desired currency and press Enter
    input_currency = page.locator('input[aria-label="Default currency"]')
    input_currency.fill(currency)
    input_currency.press("Enter")

    return page


def test_submit_expense_domain_recipient():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"])
        context = browser.new_context()
        # Start tracing
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        trace_path = "/app/expensify/user_tool/output_browser1.zip"

        try:
            # Step 1: Login user
            page, user_email = login_user(context)

            # Step 2: Start a chat or initiate workspace creation flow
            page.get_by_label("Start chat (Floating action)").click()

            # Step 3: Create a new workspace
            page.get_by_label("New workspace").click()

            # Step 4: Set the default currency to 'BDT - Tk'
            page = set_default_currency(page, "BDT - Tk")

            # Step 5: Access additional features of the workspace
            page.get_by_text("More features").click()

            # Step 6: Set up custom fields for the workspace
            page.get_by_label("Set up custom fields for").click()

            # Step 7: Upgrade the workspace to enable custom fields
            page.get_by_role("button", name="Upgrade").click()

            # Step 8: Acknowledge the upgrade with a confirmation
            page.get_by_role("button", name="Got it, thanks").click()

            # Step 9: Navigate to the 'Report fields' section
            page.get_by_test_id("WorkspaceInitialPage").get_by_text("Report fields").click()

            # Step 10: Add a new custom field
            page.get_by_role("button", name="Add field").click()

            # Step 11: Select and fill in the new custom field name
            page.get_by_test_id("CreateReportFieldsPage").get_by_text("Name").click()
            page.get_by_role("textbox", name="Name").fill("Test Field")

            # Step 12: Save the new custom field name
            page.get_by_test_id("TextSelectorModal").get_by_role("button", name="Save").click()

            # Step 13: Set the field type as 'Text'
            page.get_by_test_id("CreateReportFieldsPage").get_by_text("Type").click()
            page.get_by_label("Text").click()

            # Step 14: Save the custom field configuration
            page.get_by_role("button", name="Save").click()

            # Step 15: Navigate back to the workspace's main page
            page.get_by_test_id("WorkspaceInitialPage").get_by_label("Back").click()

            # Step 16: Open the inbox
            page.get_by_label("Inbox").click()

            # Step 17: Navigate to the workspace's chat page
            page.locator('button[aria-label="Navigates to a chat"]', has_text="A Khan's Workspace").click()

            # Step 18: Start creating a new expense report
            page.locator('button[aria-label="Create"]').last.click()

            # Step 19: Select the 'Submit expense' option
            page.get_by_text("Submit expense", exact=True).click()

            # Step 20: Choose the 'Manual' expense entry method
            page.get_by_label("Manual").click()

            # Step 21: Fill in the expense amount
            page.get_by_placeholder("0").fill("1")
            page.locator("#numPadContainerView").get_by_role("button", name="Next").click()

            # Step 22: Add the merchant information
            page.get_by_text("Merchant").click()
            page.get_by_role("textbox", name="Merchant").click()
            page.get_by_role("textbox", name="Merchant").fill("12")

            # Step 23: Save the merchant details
            page.get_by_role("button", name="Save").click()

            # Step 24: Submit the expense
            page.get_by_role("button", name="Submit BDT 1.00").click()

            # Step 25: View the submitted expense details
            page.get_by_label("View details").click()

            # Step 26: Verify that the custom field 'Test Field' is visible
            expect(page.get_by_role("menuitem").get_by_text("Test Field")).to_be_visible()

        except Exception as e:
            # Reraise to indicate test failure, but still save trace
            raise e
        finally:
            # Stop tracing and save
            context.tracing.stop(path=trace_path)
            # Clean the saved trace
            trace_cleaner(trace_path)
            browser.close()
