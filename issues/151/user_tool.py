import re
from playwright.sync_api import sync_playwright
from utils.trace_cleaner import trace_cleaner

SITE_URL = "https://dev.new.expensify.com:8082/"
PRIMARY_EMAIL = "expensifyolddot+1739802802@gmail.com"
FIRST_NAME = "Random"
LAST_NAME = "Name"
AMOUNT = 100

# Function to create an account and log in to Expensify
def create_new_account_and_login(page, user_email, first_name, last_name):
    # Create a new account as a random user
    phone_or_email_input = page.locator('input[type="email"]')
    phone_or_email_input.fill(user_email)
    page.wait_for_timeout(1000)

    # Click Continue
    continue_button = page.get_by_role("button", name="Continue")
    continue_button.click()
    page.wait_for_timeout(1000)

    # Click join button if it appears
    try:
        print("Clicking the join button again if needed")
        join_button = page.get_by_role("button", name="Join")
        join_button.click()
    except Exception as e:
        pass

    # Complete the onboarding popup
    page.wait_for_timeout(1000)
    page.locator('text="Track and budget expenses"').click()
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()
    page.wait_for_timeout(1000)

# Function to create a new workspace and return back to inbox
def create_new_workspace(page, mobile_browser=False, back_to_inbox=False):
    # Step 1: Click my settings button
    setting_button = page.locator("button[aria-label='My settings']")
    setting_button.click()

    # Step 2: Click the Workspaces menu
    preferences_div = page.locator("div[aria-label='Workspaces']:has(div:has-text('Workspaces'))")
    preferences_div.click()

    # Step 3: Click the New workspace button
    new_workspace_button = page.locator('button[aria-label="New workspace"]').last
    new_workspace_button.click()

    # Case for going back to Inbox
    if back_to_inbox:
        # Step 4: Click the back button
        back_button = page.locator('button[aria-label="Back"]')
        back_button.click()

        # For mobile browser we need to press back again to go back to inbox
        if mobile_browser:
            page.locator('button[aria-label="Back"]').last.click()

        # Step 5: Click the inbox button
        inbox_button = page.locator('button[aria-label="Inbox"]')
        inbox_button.click()

# Function to create self track expense
def create_self_track_expense(page, first_name, last_name, amount=100):
    # Step 1: Click self chat button
    page.get_by_role('button', name='Navigates to a chat').get_by_text(f'{first_name} {last_name} (you)').click()

    # Step 2: Click the '+' button to submit a new expense
    page.locator('button[aria-label="Create"]').locator("visible=true").click()

    # Step 3: Click the 'Create expense' option
    page.get_by_role('menuitem', name='Track expense').click()

    # Step 4: Click on "Manual" button
    page.get_by_role('button', name='Manual').click()

    # Step 5: Enter the amount and press enter to submit the expense
    page.locator('input[type="text"]').fill(str(amount))
    page.keyboard.press("Enter")
    page.keyboard.press("Enter")

# Rename the function based on your task name

def test_expensify_52240():
    with sync_playwright() as p:
        context = p.chromium.launch(proxy={"server": "http://localhost:8080"}, headless=False, args=["--no-sandbox", "--disable-dev-shm-usage", "--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"], slow_mo=500, channel="chromium")

        # Start tracing
        context.tracing.start(screenshots=True, snapshots=True, sources=True)

        try:
            # Create a new page in the appropriate context
            page = context.new_page()
            
            # Generate new email and create a new account
            page.goto(SITE_URL)
            create_new_account_and_login(page, PRIMARY_EMAIL, FIRST_NAME, LAST_NAME)
        
            # Create a new workspace
            create_new_workspace(page, back_to_inbox=True)
        
            # Submit self expense
            create_self_track_expense(page, FIRST_NAME, LAST_NAME, AMOUNT)
        
            # Go to search, click submitted expenses and view detail
            page.locator('button[aria-label="Search"]').click()
            page.get_by_test_id('selection-list').get_by_role('button', name='View').last.click()
            pattern = re.compile(rf"^Tracking\s+.*\b{AMOUNT}\b.*$")
            page.get_by_test_id(re.compile(r"^report-screen-")).get_by_role("button", name=pattern).last.click()
        
            # Categorize the expense
            page.get_by_role('menuitem', name='Categorize it').click()
            page.get_by_role('button', name=f"{FIRST_NAME} {LAST_NAME}'s Workspace").first.click()
            page.get_by_role('button', name='Benefits').last.click()
            page.get_by_role('menuitem', name='Merchant').click()
            page.locator('input[name="moneyRequestMerchant"]').fill("Test Merchant")
            page.keyboard.press("Enter")
            page.keyboard.press("Enter")
        
            # Go back to the expense detail
            page.get_by_test_id('selection-list').get_by_role('button', name='View').last.click()
            page.get_by_test_id(re.compile(r"^report-screen-")).get_by_role("button", name=pattern).last.click()
        
            # TEST: Verify that after categorization the track expense option is not available
            categorize_it_menu = page.get_by_role('menuitem', name='Categorize it')
            assert categorize_it_menu.count() == 0, "Categorize it menu item is still visible"
        
            submit_into_someone = page.get_by_role('menuitem', name='Submit it to someone')
            assert submit_into_someone.count() == 0, "Submit it to someone menu item is still visible"
        
        finally:
            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            context.tracing.stop(path=trace_path)
            trace_cleaner(trace_path)
            context.close()


if __name__ == "__main__":
    test_expensify_52240()