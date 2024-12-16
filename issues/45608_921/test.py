import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)


from playwright.sync_api import sync_playwright, expect

def generate_random_email():
    timestamp = 234234
    return f"expensify31+{timestamp}@gmail.com"

def login_user(page, email) -> None:

    phone_or_email_input = page.locator('input[type="email"]')
    expect(phone_or_email_input).to_be_visible()
    phone_or_email_input.fill(email)
    continue_button = page.get_by_role("button", name="Continue")
    continue_button.click()
    page.wait_for_timeout(5000)

    # Step 2: Handle login using magic code if necessary
    if not page.get_by_role("button", name="Join").is_visible():
        magic_code = "123456"
        if magic_code:
            validate_code_input = page.locator('input[data-testid="validateCode"]')
            expect(validate_code_input).to_be_visible()
            validate_code_input.fill(magic_code)
            page.wait_for_timeout(5000)
    
def reproduce_scenario(page1, page2) -> None:
    # Step 1: Perform actions on the first browser
    page1.get_by_label("My settings").click()
    page1.get_by_label("Preferences").click()
    page1.get_by_label("English").get_by_role("img").click()
    page1.get_by_label("Spanish").click()
    page1.wait_for_timeout(5000)

    # Step 2: Verify expected text on the second browser
    assert page2.get_by_text("Este es tu espacio personal").is_visible()

def test_spanish_on_lhn() -> None:
    with sync_playwright() as playwright:
        # Step 1: Launch the first browser and login
        browser1 = playwright.chromium.launch(headless=True,
                                               slow_mo=1000,
                                args=[
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                '--proxy-server=http://localhost:8080',
            ])
        context1 = browser1.new_context(ignore_https_errors=True)
        page1 = context1.new_page()
        page1.goto("https://dev.new.expensify.com:8082/")
        email = generate_random_email()
        login_user(page1, email)
        
        
        # Step 3: Launch the second browser and login
        browser2 = playwright.chromium.launch(headless=True,
                                              slow_mo=1000,
                                args=[
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                '--proxy-server=http://localhost:8080',
            ])
        context2 = browser2.new_context(ignore_https_errors=True)
        page2 = context2.new_page()
        page2.goto("https://dev.new.expensify.com:8082/")
        login_user(page2, email)


        reproduce_scenario(page1, page2)
        
        context1.close()
        browser1.close()
        context2.close()
