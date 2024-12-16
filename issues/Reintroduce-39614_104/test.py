import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright._impl._page import Page
from playwright.sync_api import sync_playwright, expect

# Constants for Email
EMAIL = "ikhanle001+4@gmail.com"


def login_user(page, user_email) -> None:
    # Open Expensify URL and log in
    page.locator('input[type="email"]').fill(user_email)
    page.wait_for_timeout(2000)
    page.get_by_role("button", name="Continue").nth(0).click()
    page.wait_for_timeout(10000)
    otp = "123456"
    page.locator('input[data-testid="validateCode"]').fill(otp)

def reproduce_scenario(page: Page) -> None:
    # Step 1: Create workspace
    page.click('//button[@aria-label="My settings"]')
    page.click('//div[@aria-label="Workspaces"]')
    page.click('//button[@aria-label="New workspace"]')

    # Step 2: Open workspace setting page
    features_text_element = page.locator('div[dir="auto"]', has_text="More features")
    features_text_element.click()

    # Step 3: Enable the taxes for the workspace
    documement_button = page.get_by_label("Document and reclaim eligible")
    documement_button.click()

    taxes_button = page.get_by_test_id("WorkspaceInitialPage").get_by_label("Taxes")
    taxes_button.click()

    # Step 4: Add taxes information
    add_rate = page.get_by_role("button", name="Add rate")
    add_rate.click()

    tax_name_button = page.get_by_test_id("WorkspaceCreateTaxPage").get_by_text("Name")
    tax_name_button.click()
    page.get_by_role("textbox", name="Name").fill("1/")

    save_button = page.get_by_test_id("TextSelectorModal").get_by_role("button", name="Save")
    save_button.click()

    tax_value_button = page.get_by_text("Value")
    tax_value_button.click()
    page.get_by_placeholder("0").fill("1")
    save_button = page.get_by_test_id("AmountSelectorModal").get_by_role("button", name="Save")
    save_button.click()

    save_button = page.get_by_role("button", name="Save").last
    save_button.click()
    page.locator("button").filter(has_text="/1%").click()

    # Verify that 'Hmm... it's not here' text is not visible
    element = page.locator('div[dir="auto"]', has_text="Hmm... it's not here")
    expect(element).not_to_be_visible()


def test_not_here_text_in_settings_page() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True,slow_mo=500, args=[
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                '--proxy-server=http://localhost:8080',
            ])
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        page.goto("https://127.0.0.1:8082/")

        # Step 1: Login user
        login_user(page, EMAIL)

        # Step 2: Reproduce scenario
        reproduce_scenario(page)

        page.wait_for_timeout(1000)

        context.close()
        browser.close()