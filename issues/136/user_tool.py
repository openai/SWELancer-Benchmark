from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page
from utils.trace_cleaner import trace_cleaner


# Utility to generate an email
def generate_email():
    timestamp = '52202001'
    return f"freelanceapptest+{timestamp}@gmail.com"


# Function to log in the user and complete onboarding steps
def login_user(p: PlaywrightContextManager, first_name="Milan", last_name="T") -> tuple[Browser, Page, str]:
    # Launch Chromium and open a new page in a mobile device view
    device = p.devices["iPhone 13"]
    browser = p.chromium.launch(
        channel="chrome",
        headless=False,
        args=[
            "--ignore-certificate-errors",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ],
        proxy={"server": "http://localhost:8080"},
        slow_mo=1000
    )

    context = browser.new_context(ignore_https_errors=True, **device)
    page = context.new_page()
    user_email = generate_email()

    # Step 1: Open the Expensify URL
    page.goto('https://dev.new.expensify.com:8082/') 

    # Step 2: Enter a generated email and click continue
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(1000) 

    # Step 3: Click the join button if available otherwise skip
    try: 
        page.locator('button[tabindex="0"]').click() 
        page.wait_for_timeout(1000) 
    except Exception:
        pass

    # Step 4: Ensure that the user reaches the dashboard by checking for visible text
    expect(page.locator("text=What do you want to do today?")).to_be_visible()
        
    # Step 5: Select 'Track and budget expenses' on the onboarding page and click Continue
    page.locator("text='Track and budget expenses'").click()
    page.wait_for_timeout(1000) 

    # Step 6: Enter first name last name, and continue
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()
    page.wait_for_timeout(1000) 

    return browser, page


def submit_multiple_expenses(page, amounts, emails):
    """
    Creates and submits multiple expenses using the provided lists of amounts and emails.

    :param amounts: List of amounts (e.g., [100, 200])
    :param emails: List of recipient emails (e.g., ["test01@gmail.com", "test02@gmail.com"])
    """

    for amount, email in zip(amounts, emails):
        # Step 1: Navigate to start a new expense submission
        page.get_by_label("Start chat (Floating action)").click()
        page.get_by_text("Submit expense").first.click()

        # Step 2: Choose Manual Expense
        page.get_by_label("Manual").click()

        # Step 3: Select the currency
        page.get_by_label("Select a currency").click()
        page.get_by_test_id("selection-list-text-input").fill("USD")
        page.get_by_label("USD - $").click()

        # Step 4: Enter the expense amount
        page.get_by_placeholder("0").fill(str(amount))
        page.locator("#numPadContainerView").get_by_role("button", name="Next").click()

        # Step 5: Enter the recipient email
        page.get_by_test_id("selection-list-text-input").fill(email)
        page.get_by_label(email).click()

        # Step 6: Submit the expense
        page.get_by_role("button", name="Submit $").click()

        # Step 7: Navigate back to submit another expense
        page.get_by_label("Back").last.click()


def test_select_expense_by_tapping_and_holding():
    with sync_playwright() as p:
        browser, page = login_user(p)
        context = page.context
        # Start tracing
        context.tracing.start(screenshots=True, snapshots=True, sources=True)

        try:
            # Step 1: Login as a new user and return to the main navigation page
            if page.get_by_text("Welcome to Expensify").is_visible():
                page.get_by_label("Back").click()

            # Step 2: Submit multiple expenses
            amounts = [100, 250, 500, 800]
            emails = ["test01@gmail.com", "test02@gmail.com", "test03@gmail.com"]

            submit_multiple_expenses(page, amounts, emails)

            # Step 3: Go to the Expensify search page, tap and hold one of the expenses
            page.get_by_role("button", name="Search").click()
            expense = page.get_by_role("button", name="Milan T test02@gmail.com $")
            expense.hover()
            page.mouse.down(button="left")
            page.wait_for_timeout(2000)
            page.mouse.up(button="left")

            # Step 4: Assert that the select button is visible
            assert page.get_by_text("Select").is_visible(), "Unable to select expenses by tapping and holding on the expense"
        finally:
            # Stop tracing and export the trace file
            trace_file_path = "/app/expensify/user_tool/output_browser1.zip"
            context.tracing.stop(path=trace_file_path)
            trace_cleaner(trace_file_path)
            browser.close()


if __name__ == "__main__":
    test_select_expense_by_tapping_and_holding()
