import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from playwright._impl._page import Page


# Utility to generate a random email
def generate_random_email():
    timestamp = 48920
    return f"expensify31+{timestamp}@gmail.com"


def login_user(page: Page, first_name="Milan", last_name="T") -> tuple[Page, str]:
    # Launch chromiun and open new page
    user_email = generate_random_email()

    # Step 1: Open expensify url
    page.goto('https://dev.new.expensify.com:8082/')

    # Step 2: Enter email and click continue
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(1000)

    # Step 3: Click join button
    try:
        page.locator('button[tabindex="0"]').click()
        expect(page.locator("text=What do you want to do today?")).to_be_visible()

        # Step 4: Select 'Track and budget expenses' in onobarding page and click Continue
        page.locator("text='Track and budget expenses'").click()
        page.get_by_role("button", name="Continue").click()

        # Step 5: Enter first name, last name and click continue
        page.locator('input[name="fname"]').fill(first_name)
        page.locator('input[name="lname"]').fill(last_name)
        page.get_by_role("button", name="Continue").last.click()
    except Exception:
        # Step 3: Get the OTP code from the email
        page.wait_for_timeout(2000)
        otp = "123456"

        # Enter the OTP code
        page.locator('input[name="validateCode"]').fill(otp)

    return page, user_email

def test_lhn_default_text():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="chrome",
            headless=True,
            args=[
                "--ignore-certificate-errors",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process"
            ],
            proxy={"server": "http://localhost:8080"},
            slow_mo=700
        )
        context = browser.new_context()
        page = context.new_page()

        # Step 1: Login user
        login_user(page)

        # Check that the text does not exist
        dm_preview = page.locator('div[aria-label="Last chat message preview"]', has_text="This is the beginning of your chat")
        expect(dm_preview).not_to_be_visible()

