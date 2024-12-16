import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
import re

expensify_email = "totherandomuser+50419@gmail.com"

def login(p, context):
    page = context.new_page()
    page.goto('https://dev.new.expensify.com:8082')

    # Step 1: Enter username and continue
    page.get_by_test_id("username").click()
    page.get_by_test_id("username").fill(expensify_email)
    page.get_by_role("button", name="Continue").click()

    # Step 2: Get Magic code static in this case
    magic_code = "123456"

    # Step 3: Fill in the magic code
    validate_code_input = page.locator('input[name="validateCode"]')
    expect(validate_code_input).to_be_visible()
    validate_code_input.fill(magic_code)
    page.wait_for_timeout(1000)

    return page


def test():
    with sync_playwright() as p:

        # Step 1: Main Browser Login
        browser = p.chromium.launch(headless=True,slow_mo=1000, args=[
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                '--proxy-server=http://localhost:8080',
            ])
        context = browser.new_context()
        page = login(p, context)

        # Step 2: Create a workspace in setting.
        page.get_by_label("My settings").click()
        page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()
        page.get_by_label("New workspace").last.click()
        page.get_by_label("Back").last.click()

        elements = page.locator("div").all_inner_texts()
        new_workspace = []
        # Search for the workspace name using a regular expression
        for text in elements:
            match = re.search(r"John's Workspace \d+", text)
            if match:
                workspace_name = match.group(0)
                new_workspace.append(workspace_name)                
        
        new_workspace = new_workspace[-1]
        page.get_by_label("Inbox").click()

        # Step 3 Go to workspace and create an expense with random merchant name.
        merchant_name = '34234'
        page.locator('button[aria-label="Navigates to a chat"]', has_text=new_workspace).last.click()
        page.get_by_label("Create").last.click()
        page.get_by_text("Submit expense", exact=True).click()
        page.get_by_label("Manual").click()
        select_currency_button = page.locator(
            'button[aria-label="Select a currency"]').nth(-1)
        page.wait_for_timeout(2000)

        # Locate the div inside the button
        div_inside_button = select_currency_button.locator('div').nth(-1)

        # Get the text content of the div
        default_currency = div_inside_button.text_content().strip()
        page.get_by_placeholder("0").fill("500")
        page.locator("#numPadContainerView").get_by_role("button", name="Next").click()
        page.get_by_role("menuitem", name="Merchant Required").click()
        page.get_by_role("textbox", name="Merchant").click()
        page.get_by_role("textbox", name="Merchant").fill(merchant_name)
        page.get_by_role("button", name="Save").click()
        page.get_by_role("button", name=f"Submit {default_currency}").click()


        # navigate to the search page
        page.get_by_test_id("CustomBottomTabNavigator").get_by_label("Search").click()

        # Select the first report
        page.get_by_role("button", name=merchant_name).click()

        page.wait_for_timeout(2000)

        # Change the category
        page.get_by_text("Category").last.click()
        page.get_by_label("Advertising").click()

        # Add a 2nd message
        page.locator("#composer").last.fill("Heya 2")
        page.locator("#composer").last.press("Enter")

        # App should maintain the editor in the RHN
        expect(page.get_by_text("John (you)")).not_to_be_visible()

