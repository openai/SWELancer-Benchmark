from playwright.sync_api import sync_playwright

user_email = "testuserexpensify1@gmail.com"
password = ""
user_id = "testuserexpensify1+155@gmail.com"

def login(p, if_phone=False, first_name="John", last_name="Doe"):
    
    # step 1: Login
    permissions = ['clipboard-read']
    browser = p.chromium.launch(headless=False, slow_mo=1000, args=["--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"])

    if if_phone:
        phone = p.devices['Pixel 7']
        context = browser.new_context(**phone, permissions=permissions, reduced_motion='no-preference')
    else:
        context = browser.new_context()

    page = context.new_page()

    page.goto('https://dev.new.expensify.com:8082/') 

    phone_or_email_input = page.locator('input[type="email"]')
    phone_or_email_input.fill(user_id)

    continue_button = page.locator('button[tabindex="0"]')
    continue_button.click()
    magic_code = "123456"

    validate_code_input = page.locator('input[name="validateCode"]')
    validate_code_input.fill(magic_code)

    return browser, page

def close_modal(page):
    """Attempts to close a modal if it exists."""
    try:
        page.locator('button[aria-label="Close"]').click(timeout=3000)
    except Exception:
        pass  # Modal might not be present, safely ignore the exception

def test_53918():
    with sync_playwright() as p:
        browser, page = login(p, False)
        close_modal(page)
        close_modal(page)
        page.get_by_test_id("CustomBottomTabNavigator").locator('button[aria-label="My settings"]').click()
        close_modal(page)
        page.get_by_test_id("CustomBottomTabNavigator").locator('div[aria-label="Subscription"]').click()
        page.get_by_test_id("SubscriptionSettingsPage").locator('div[dir="auto"]', has_text="Add payment card").click()
        page.get_by_test_id("AddPaymentCard").locator('div[aria-label="Zip / Postcode"] input[role="presentation"]').fill("2@,:;")
        page.keyboard.press("Enter")
        zip_container = page.get_by_test_id("AddPaymentCard").locator('div[aria-label="Zip / Postcode"]')
        parent_element = zip_container.locator("..")
        error_icon = parent_element.locator('svg[fill="#F25730"]')
        # Assert that at least one error icon exists within the parent
        assert error_icon.count() > 0, "Error message is not displayed when entering characters that cannot be in a zip code"
        browser.close()