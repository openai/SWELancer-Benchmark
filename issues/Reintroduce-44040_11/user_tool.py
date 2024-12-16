import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from utils.trace_cleaner import trace_cleaner

EMAIL_USERNAME = "aliceoglualice+44040_0001@gmail.com"
EMAIL_PASSWORD = "cfpy ofxm lcmq aeta"

first_name = "Sujil"
last_name = "Devkota"
site_url = "https://dev.new.expensify.com:8082/"


# Base function to create an account and log in to Expensify
def create_new_account_and_login(page, first_name, last_name):
    user_email = EMAIL_USERNAME
    page.goto(site_url)

    # Create a new account as a random user
    phone_or_email_input = page.locator('input[type="email"]')
    expect(phone_or_email_input).to_be_visible()
    phone_or_email_input.fill(user_email)
    page.wait_for_timeout(1000)

    # Click Continue
    continue_button = page.locator('button[tabindex="0"]')
    expect(continue_button).to_be_visible()
    continue_button.click()
    page.wait_for_timeout(3000)

    # Check if OTP is required for the login
    try:
        expect(page.get_by_test_id("SignInPage").get_by_test_id("validateCode")).to_be_visible(timeout=5000)
    except (AssertionError, TimeoutError):
        # If not required, expect the join button to appear and click the button
        page.get_by_test_id("SignInPage").get_by_role("button", name="Join").click()
    else:
        # Get the OTP and complete verification
        otp_code = "123456"
        otp_input = page.locator('input[autocomplete="one-time-code"]')
        otp_input.fill(otp_code)

    # Check if onboarding is required
    try:
        expect(page.get_by_text("What do you want to do today?")).to_be_visible(timeout=5000)
    except (AssertionError, TimeoutError):
        pass
    else:
        # Complete the onboarding
        page.get_by_label("Track and budget expenses").click()
        page.get_by_role("textbox", name="First name").fill(first_name)
        page.get_by_role("textbox", name="Last name").fill(last_name)
        page.get_by_role("button", name="Continue").click()

    return user_email

# Function to submit an expense to a specific user
def submit_expense(page, recipient_email):
    # Step 1: Click the '+' button to start chat
    plus_button = page.locator('button[aria-label="Start chat (Floating action)"]')
    expect(plus_button).to_be_visible()
    plus_button.click()
    page.wait_for_timeout(1000)

    # Step 2: Click the 'Submit expense' button
    submit_expense_button = page.locator('div[aria-label="Submit expense"]')
    expect(submit_expense_button).to_be_visible()
    submit_expense_button.click()
    page.wait_for_timeout(1000)

    # Step 3: Click on "Manual" button and upload a receipt
    manual_button = page.locator('button[aria-label="Manual"]')
    expect(manual_button).to_be_visible()
    manual_button.click()
    page.wait_for_timeout(1000)

    # Step 4: Enter the amount and press enter
    page.locator('input[type="text"]').fill("500")
    page.keyboard.press("Enter")
    page.wait_for_timeout(1000)

    # Step 5: Enter the recipient email to send the receipt
    email_input = page.locator('input[aria-label="Name, email, or phone number"]')
    expect(email_input).to_be_visible()
    email_input.fill(recipient_email)
    page.wait_for_timeout(1000)

    # Step 6: Click div with the recipient email and submit
    recipient_option = page.locator(f'div:has-text("{recipient_email}")').last
    expect(recipient_option).to_be_visible()
    recipient_option.click()
    page.wait_for_timeout(1000)
    page.keyboard.press("Enter")
    page.wait_for_timeout(1000)

# Test to verify the members appear in the model
def test_expenses_members_list():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=[
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
            "--ignore-certificate-errors"
        ])

        # Record trace
        context = browser.new_context()
        trace_path = "/app/expensify/user_tool/output_browser1.zip"
        context.tracing.start(screenshots=True, snapshots=True, sources=True)

        page = context.new_page()
        try:
            # Create accounts and login for both users
            user1_email = create_new_account_and_login(page, first_name + "1", last_name + "1")
            user2_email = "test_email1235_test@gmail.com"

            # User 1 submits an expense to User 2
            submit_expense(page, user2_email)

            # Test: Open members model
            page.locator('div[dir="auto"]:has-text("500.00")').last.click()
            page.locator('div[dir="auto"]:has-text("owes")').last.click()
            page.locator('div[dir="auto"]:has-text("Members")').last.click()

            # Verify first user is visible
            user_div = page.locator(f'button[aria-label*="{first_name}1"]:has(div:has-text("{user1_email}"))')
            expect(user_div).to_be_visible()
        except Exception as e:
            # Reraise the error after finishing the trace
            raise e
        finally:
            # Ensure the trace is always stopped and saved, then cleaned
            context.tracing.stop()
            context.tracing.export(trace_path)
            trace_cleaner(trace_path)

        browser.close()
