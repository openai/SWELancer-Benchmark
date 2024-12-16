import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from playwright._impl._page import Page


# Email login credentials
EMAIL_USERNAME = "testotpverif@gmail.com"
EMAIL_PASSWORD = "ghka tmuf vpio patv"
EXPENSIFY_URL = "https://dev.new.expensify.com:8082/"


# Function to login a user
 
def login_user(page):
    """
    Log into the Expensify app.
    """
    # Open the Expensify app
    page.goto(EXPENSIFY_URL)
    # Login user
    page.get_by_test_id("username").fill(EMAIL_USERNAME)
    page.get_by_role("button", name="Continue").click()
    # Check if OTP is required for the login
    otp_code = "123456"
    page.get_by_test_id("SignInPage").get_by_test_id("validateCode").fill(otp_code)
    # page.get_by_test_id("SignInPage").get_by_role("button", name="Sign in").click()
    page.wait_for_timeout(2000)

def test_composer():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, slow_mo=500, args=[
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ])
        context = browser.new_context()
        page = context.new_page()

        # Step 1: Login user 
        login_user(page)

        personal_chat = page.get_by_text(f"Test (you)")
        expect(personal_chat).to_be_visible()
        personal_chat.click()
        page.wait_for_timeout(1000)

        # Type some text
        page.keyboard.type("Line 1")

        # Simulate Shift + Enter
        page.keyboard.down('Shift')
        page.keyboard.press('Enter')
        page.keyboard.up('Shift')

        # Type the next line of text
        page.keyboard.type("Line 2")
        
        # Simulate Shift + Enter again
        page.keyboard.down('Shift')
        page.keyboard.press('Enter')
        page.keyboard.up('Shift')

        page.wait_for_timeout(2000)

        # Retrieve the content of the contenteditable div and assert it matches the entered text
        content = page.evaluate('''() => {
            const paragraphs = document.querySelectorAll("div[role='textbox'][aria-placeholder='Write something...'] p");
            return Array.from(paragraphs).map(p => p.innerText).join("\\n");
        }''').replace("\n\n", "\n")
        
        # Perform the check
        assert content == "Line 1\nLine 2\n", f"Expected 'Line 1\nLine 2\n' but got '{content}'"