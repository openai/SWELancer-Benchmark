import os
import shutil
from playwright.sync_api import sync_playwright


SITE_URL = "https://dev.new.expensify.com:8082/"
PRIMARY_EMAIL = "expensifyolddot@gmail.com"
FIRST_NAME = "Random"
LAST_NAME = "Name"
MOBILE_BROWSER = False
MOBILE_DEVICE_NAME = "Pixel 7"
new_timestamp = 17400691704234234450
USER_DATA_DIR = f"expensify_session_{new_timestamp}"  # Directory to store session data
EMAIL_FILE_PATH = os.path.join(USER_DATA_DIR, 'user_email.txt')
BROWSER_WIDTH = 1280
BROWSER_HEIGHT = 720
TIMESTAMP = 17400691704234234450
WORKSPACE_NAME = f"Random Name's Workspace {TIMESTAMP}"

QUICKBOOK_DATA = """
    {
        config: {
            companyName: 'test',
            credentials: {
                access_token:
                    '2LHOKnH9waofJaMRyrVBUP+4qJsh4u+6E3Ffu73YJFJ6FnzAfsydZVkVFwjQmyxknEXCOYNeqoRljafcUk2sgzeq6002fXY55AEKF36UjaQQskfo4wR192K0v/68BUEzCpghfahoRmupoNq0u1JM8h/NDNIcLEi9ZDBno+7a22wi2jshJtcGL/wGBMUalWFupOmkiJbLPFen+mHFqLI8kF4TydI2a7SC4M4BAkZ2N7cFvp9LC39cLvrL7pZ/0wdIe8d4AMrKdR8M8V+KD8r2X4zXoQhKxSPA+2wRFiXIwOKB2iZqgI19dQHD0QqwbW6a512nOb7Q1Y0/SrF6NtVAaBXwhF2o3VULwFH3cy4QTYxB25wXCU76bhYsvUaQ/xWUVjY2TEi3GXkdTrNN8Ys8MXH3A9kVX7I32whBMfygcjYLtxc4/aVr8gYg8w5XPRRJ5Q/OGy68mX1JlCyWi+1NNAUJVkeRXuOsnivYvvaRisCJ4bng4ZiK9hnSWJ6qyKMWnb/nPpjZfZe25nbXfEG/e3CgwJ3KU4RlWZM+ECSWGcM/KyAGfErbcDBXXQk/6BnMjTqQkP5HotH8BHsUzYsw8D1A8i3gpgU/CStK8b+2PFcoqgTxWmsPgL7O32AFNR6z1yd1Zsrk5cDVHDlTddw1ePxrvfJRuT7gNKlut9oIAjgyR5iagxk/By2AGp0o2S53becAoPRGtuYYxk5WmpfB2q0N0QHI9VtRDJ5p1wn4KPO4twnnkU5YyD/u2UuBCWw9UB1rDWZVpGRUilyF2/0vy7PJHoUCXodz0DIulT+cDSHqf9hmc1pm7LI3Qt17X4uO1YCIQA7qQk1G5aY32HwNVq2VnyZJT64nEJ3JMydI4k74jrGy9Zp+52lAF39AenCaNjbVJg5svd0KEeOdwqr1j9SNkrHZkMmhuAUSI/WfyAhrtmjmRVGBTJ6b9l8fjdzwLwubXdFInG8M7h8Pc0Db7VTvd8Qv8MFRjhomzHbTkVMApKr1EH9WGzf932FlDse9HwKC4c6mA2Uj0BCaxsbnKnqd/I6Ug==;vJoXwrJgPzNOdv28yQHtPA==;eKPhE8t3aDV62W1np/MZoKIYA1bRawdFuttb5yxT44HQWjYgEc5x/Glx+Ye6YZP06Aj3N0A7eMw6rj98Kjpaow==',
                companyID: '934145206296',
                companyName: 'test',
                expires: 1730725016,
                realmId: '934145340296',
                refresh_token:
                    'KwizVqdImwI5kHeImQ2NrXO7rteCSzvtQakR3uhp7Y04X06z3F4Hvt42jw==;fK/XjysVFPC4lYgRXbzi/RpxI1z3aWWpaLSAnT5v1kRtg4ilXX9fjQvA6Wc3LhKqZXnADugm2DbveEmZWAItlg==',
                scope: 'Accounting',
                token_type: 'bearer',
            },
            realmId: '9341453405206',
            autoSync: {
                enabled: true,
                jobID: '4604867689969023701',
            },
            syncClasses: 'REPORT_FIELD',
            pendingFields: {},
            errorFields: {},
            syncLocations: 'NONE',
            autoCreateVendor: false,
            collectionAccountID: '29',
            enableNewCategories: true,
            export: {
                exporter: 'zhenja3033@gmail.com',
            },
            exportDate: 'REPORT_EXPORTED',
            hasChosenAutoSyncOption: true,
            lastConfigurationTime: 1730721696740,
            markChecksToBePrinted: false,
            nonReimbursableBillDefaultVendor: 'NONE',
            nonReimbursableExpensesAccount: {
                currency: 'PLN',
                glCode: '',
                id: '29',
                name: 'Cash and cash equivalents',
            },
            nonReimbursableExpensesExportDestination: 'debit_card',
            reimbursableExpensesAccount: {
                currency: 'PLN',
                glCode: '',
                id: '29',
                name: 'Cash and cash equivalents',
            },
            reimbursableExpensesExportDestination: 'bill',
            reimbursementAccountID: '29',
            syncCustomers: 'TAG',
            syncItems: false,
            syncPeople: false,
            syncTax: false,
        },
        data: {
            accountPayable: [],
            accountsReceivable: [],
            bankAccounts: [
                {
                    currency: 'PLN',
                    glCode: '',
                    id: '29',
                    name: 'Cash and cash equivalents',
                },
            ],
            country: 'PL',
            creditCards: [],
            edition: 'QuickBooks Online Simple Start',
            employees: [],
            homeCurrency: 'PLN',
            isMultiCurrencyEnabled: false,
            journalEntryAccounts: [
                {
                    currency: 'PLN',
                    glCode: '',
                    id: '32',
                    name: 'Accrued liabilities',
                },
            ],
            otherCurrentAssetAccounts: [
                {
                    currency: 'PLN',
                    glCode: '',
                    id: '70',
                    name: 'Allowance for bad debt',
                },
            ],
            vendors: [],
        },
        lastSync: {
            errorDate: '',
            errorMessage: '',
            isAuthenticationError: true,
            isConnected: true,
            isSuccessful: true,
            source: 'NEWEXPENSIFY',
            successfulDate: '2024-11-04T12:01:36+0000',
        },
    }
"""

# Function to create an account and log in to Expensify
def create_new_account_and_login(page, user_email, first_name, last_name):
    # Create a new account as a random user
    phone_or_email_input = page.locator('input[type="email"]')
    phone_or_email_input.fill(user_email)
    page.wait_for_timeout(1000)

    # Click Continue
    continue_button = page.locator('button[tabindex="0"]')
    continue_button.click()
    page.wait_for_timeout(1000)

    # Click join button if it appears
    try:
        print("Clicking the join button again if needed")
        continue_button.click()
    except Exception as e:
        pass

    # Complete the onboarding page
    page.locator("text='Track and budget expenses'").click()
    page.wait_for_timeout(1000)
    # Fill in the first and last name and click Continue
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()
    page.wait_for_timeout(1000)

# Generate a random email address based on the primary email
def generate_random_email(email):
    # timestamp = int(time.time())
    timestamp = 17400691704234234450
    return f"{email.split('@')[0]}+{timestamp}@{email.split('@')[1]}"

# Save the generated email to a file in the session directory
def save_email_to_file(email, email_file_path):
    with open(email_file_path, 'w') as f:
        f.write(email)

# Load the saved email from the session directory
def load_email_from_file(email_file_path):
    if os.path.exists(email_file_path):
        with open(email_file_path, 'r') as f:
            return f.read().strip()
    return None

# Function to create a new workspace and return back to inbox
def create_new_workspace(page, mobile_browser=False, back_to_inbox=False):

    page.goto("https://dev.new.expensify.com:8082/settings/workspaces/")


    # Step 2: Click the Workspaces menu
    # preferences_div = page.locator("div[aria-label='Workspaces']:has(div:has-text('Workspaces'))")
    # preferences_div.click()

    # Step 3: Click the New workspace button
    new_workspace_button = page.locator('button[aria-label="New workspace"]').last
    new_workspace_button.click()

    default_currency_element  = page.get_by_text("Default currency").last
    default_currency_element .click()
    page.get_by_test_id("selection-list-text-input").fill("usd")

    currency_input_element  = page.get_by_label("USD - $")
    currency_input_element .click()

    page.get_by_test_id("WorkspacePageWithSections").get_by_label("Random Name's Workspace").get_by_role("img").click()
    page.get_by_role("textbox", name="Name").click()
    page.get_by_role("textbox", name="Name").press("ControlOrMeta+a")
    page.get_by_role("textbox", name="Name").fill(WORKSPACE_NAME)
    page.get_by_role("button", name="Save").click()

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

# Function to Enable accounting feature
def enable_workspace_accounting(page):
    # Step 1: Click More features button
    more_features_option = page.locator('div[aria-label="More features"]')
    more_features_option.click()

    # Step 2: Enable Accounting feature ON
    accounting_toggle = page.locator('button[aria-label="Sync your chart of accounts and more."][role="switch"]')
    if accounting_toggle.get_attribute('aria-checked') == "false":
        accounting_toggle.click()

    # Step 3: Click Accounting option
    accounting_option = page.locator('div[aria-label="Accounting"]')
    accounting_option.click()

# Function to connect to third-party accounting software
def connect_to_accounting_software(page, accounting_software):

    # Step 2: Upgrade the account if the upgrade window appear
    upgrade_button = page.locator('button:has(div:has-text("Upgrade"))')
    if upgrade_button.is_visible():
        upgrade_button.click()
        page.keyboard.press("Enter")  # Press enter to confirm upgrade
        page.locator('button[aria-label="Back"]').last.click() # Click back to dismiss the popup
        # connect_button.click() # Click the connect button again
    page.wait_for_timeout(1000)

    # Step 3: Apply the patch for Quickbooks Online to connect
    policy_id = page.url.split("/workspaces/")[1].split("/")[0]
    if accounting_software == "Quickbooks Online":
        page.evaluate(
            f"""
            Onyx.merge('policy_{policy_id}', {{
                "connections": {{ "quickbooksOnline": {QUICKBOOK_DATA} }}
            }});
            """
        )

    # Step 4: Close the popup or new tab
    page.wait_for_timeout(2000)
    if accounting_software == "Netsuite":
        page.locator('button[aria-label="Back"]').last.click() # Click back to dismiss the popup
    elif accounting_software == "Quickbooks Online":
        new_tab = page.context.pages[-1] # Detect and close the newly opened tab
        _ = new_tab.url
        new_tab.wait_for_load_state("domcontentloaded")
        if new_tab != page:
            new_tab.close()



def check_overlap(page,workspace_id):
    # Locate the first element (button)
    button_locator = page.locator("button").filter(has_text=f"Random Name's Workspace {TIMESTAMP} paid: $6.00eExport to QuickBooks Online")
    
    # Locate the second element (#composer inside report-screen)
    composer_locator = page.get_by_test_id(f"report-screen-{workspace_id}").locator("#composer")

    # Get the bounding boxes
    button_box = button_locator.bounding_box()
    composer_box = composer_locator.bounding_box()

    # Ensure both elements were found
    assert button_box is not None, "Button bounding box not found"
    assert composer_box is not None, "Composer bounding box not found"

    # Function to check overlap
    def is_overlapping(box1, box2):
        return not (
            box1["x"] + box1["width"] <= box2["x"] or
            box2["x"] + box2["width"] <= box1["x"] or
            box1["y"] + box1["height"] <= box2["y"] or
            box2["y"] + box2["height"] <= box1["y"]
        )

    # Check for overlap
    overlap = is_overlapping(button_box, composer_box)
    return overlap
    



# Rename the function based on your task name
def test_expensify_50357():
    with sync_playwright() as p:
        try:
            shutil.rmtree(USER_DATA_DIR, ignore_errors=True)
        except Exception as e:
            pass
        if MOBILE_BROWSER:
            mobile_device = p.devices[MOBILE_DEVICE_NAME]
            # Launch browser with mobile emulation settings
            context = p.chromium.launch_persistent_context(
                user_data_dir=USER_DATA_DIR,
                headless=False,
                user_agent=mobile_device['user_agent'],
                viewport=mobile_device['viewport'],
                slow_mo=500,
                args=['--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
            '--proxy-server=http://localhost:8080',
]
            )
        else:
            # Launch browser in persistent context without mobile emulation
            context = p.chromium.launch_persistent_context(user_data_dir=USER_DATA_DIR,
                    headless=False,
                    viewport={'width': BROWSER_WIDTH, 'height': BROWSER_HEIGHT},
                    slow_mo=500,
                    args=['--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
            '--proxy-server=http://localhost:8080'])

        # Create a new page in the appropriate context
        page = context.new_page()
    
        # Check if we need to create a new account or log in
        page.goto(SITE_URL)
        page.wait_for_timeout(1000)
        if page.locator('input[type="email"]').is_visible():
            print("No existing session found, creating a new account and logging in.")
            user_email = generate_random_email(PRIMARY_EMAIL)
            create_new_account_and_login(page, user_email, FIRST_NAME, LAST_NAME)
            save_email_to_file(user_email, EMAIL_FILE_PATH)
        else:
            print("Existing session found, continuing with logged-in session.")
            user_email = load_email_from_file(EMAIL_FILE_PATH)

        # Step 1: Create new workspace
        create_new_workspace(page, MOBILE_BROWSER)

        # Step 2: Enable accounting feature
        enable_workspace_accounting(page)
        page.wait_for_timeout(1000)

        # Step 3: Connect to accounting software
        connect_to_accounting_software(page, "Quickbooks Online")
        page.wait_for_timeout(1000)

        
        page.get_by_test_id("WorkspaceInitialPage").get_by_label("Random Name's Workspace").get_by_text("Random Name's Workspace").click()

        # # Click WS chat
        # click_WS_chat = page.locator(
        #     'button[aria-label="Navigates to a chat"]', has_text=WORKSPACE_NAME).nth(-1)
        # click_WS_chat.click()


        pageurl = page.url
        workspace_id = pageurl.split("/")[-1]

        page.get_by_test_id(f"report-screen-{workspace_id}").get_by_label("Create").click()
        page.get_by_text("Submit expense", exact=True).click()
        page.get_by_label("Manual").last.click()
        page.get_by_placeholder("0").fill("5")
        page.locator("#numPadContainerView").get_by_role("button", name="Next").click()
        page.get_by_text("Description").last.click()
        page.get_by_role("textbox", name="What's it for?").fill("a")
        page.get_by_role("button", name="Save").click()
        page.get_by_text("Merchant").last.click()
        page.get_by_role("textbox", name="Merchant").fill("b")
        page.get_by_role("button", name="Save").click()
        page.get_by_role("button", name="Submit $").click()

        if page.get_by_role("button", name="Got it").is_visible():
            page.get_by_role("button", name="Got it").click()
        page.get_by_label("View details").get_by_role("button").nth(1).click()
        page.get_by_text("Pay $5.00 elsewhere").click()
        page.get_by_role("button", name="Pay $5.00 elsewhere").click()
        page.get_by_test_id(f"report-screen-{workspace_id}").get_by_label("Create").click()
        page.get_by_text("Submit expense", exact=True).click()
        page.get_by_label("Manual").last.click()
        page.get_by_placeholder("0").click()
        page.get_by_placeholder("0").fill("6")
        page.locator("#numPadContainerView").get_by_role("button", name="Next").click()
        page.get_by_text("Description").last.click()
        page.get_by_role("textbox", name="What's it for?").fill("d")
        page.get_by_role("button", name="Save").click()
        page.get_by_text("Merchant").last.click()
        page.get_by_role("textbox", name="Merchant").fill("e")
        page.get_by_role("button", name="Save").click()
        page.get_by_role("button", name="Submit $").click()
        page.get_by_role("button", name="Pay $6.00 elsewhere").click()
        overlap = check_overlap(page=page,workspace_id=workspace_id)
        try:
            shutil.rmtree(USER_DATA_DIR, ignore_errors=True)
        except Exception as e:
            pass
        assert not overlap, "The elements overlap"

        page.wait_for_timeout(2000)
