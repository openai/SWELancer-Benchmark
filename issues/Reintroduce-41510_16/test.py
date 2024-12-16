import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager

GMAIL_NAME = "aliceoglualice"
GMAIL_APP_PASSWORD = "cfpy ofxm lcmq aeta"


def get_test_user_info(seed=None, first_name=None, last_name=None):
    if first_name is None:
        first_name = GMAIL_NAME

    if last_name is None:
        last_name = ""

    email = (
        f"{GMAIL_NAME}+{seed}@gmail.com"
        if seed is not None
        else f"{GMAIL_NAME}@gmail.com"
    )

    return {
        "email": email,
        "password": GMAIL_APP_PASSWORD,
        "first_name": first_name,
        "last_name": last_name,
    }

def select_activity(page, first_name, last_name, activity_text):
    # Select activity in onboarding page and click Continue
    page.get_by_label(activity_text).click()

    # Enter first name, last name and click continue
    page.get_by_role("textbox", name="First name").fill(first_name)
    page.get_by_role("textbox", name="Last name").fill(last_name)
    page.get_by_role("button", name="Continue").last.click()


def login_user(page, user_info, activity_text="Track and budget expenses"):
    page.goto("https://dev.new.expensify.com:8082/")
    page.wait_for_load_state("load")

    page.locator('input[type="email"]').fill(user_info["email"])
    page.get_by_role("button", name="Continue").click()

    join_button = page.get_by_role("button", name="Join")
    validate_code_input = page.locator('input[data-testid="validateCode"]')
    expect(join_button.or_(validate_code_input)).to_be_visible()

    if join_button.is_visible():
        join_button.click(timeout=3000)
    else:
        validate_code_input.fill("123456")

    page.wait_for_timeout(3000)

    select_activity_dialog = page.get_by_text("What do you want to do today?")
    if select_activity_dialog.count() > 0:
        select_activity(
            page, user_info["first_name"], user_info["last_name"], activity_text
        )


def test_payment_text():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=[
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
            "--ignore-certificate-errors"
        ])
        user_info = get_test_user_info(seed=415100001, first_name="Alice")
        page = browser.new_page()
        login_user(page, user_info)

        # Step 2: create task to asign
        page.get_by_label("Start chat (Floating action)").click()
        page.locator('div[aria-label="Start chat"][role="menuitem"]').click()
        # Locate the input field
        input_field = page.locator('input[aria-label="Name, email, or phone number"]')
        # Fill the field with the new value
        test_email = "test_41510_email_001@gmail.com"
        input_field.fill(test_email)
        page.locator(f'div[dir="auto"]:has-text("test_41510_email_001@gmail.com")').last.click()
        page.wait_for_timeout(1000)
        create_btn = page.locator('button[aria-label="Create"]').last
        create_btn.click()
        page.get_by_label("Assign task").click()

        # Step 3: Enter the test task
        page.get_by_role("textbox", name="Title").fill("test task")
        page.get_by_role("textbox", name="Title").press("Enter")

        # Step 4: Select assignee and check if the test assign to me is visible
        page.get_by_role("menuitem", name="Assignee").click()
        expect(page.get_by_text("Assign to me")).to_be_visible()

        # Close browser
        browser.close()

