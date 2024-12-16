import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
import re

original_email = "nitish.expensify@gmail.com"
APP_PASSWORD = "ojhi eovp lbkz ktfb"


def get_user_email():
    return f"nitish.expensify+{72}@gmail.com"


def get_magic_code():
    return "123456"


def login_user(p: PlaywrightContextManager):
    browser = p.chromium.launch(headless=True, args=[
        "--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"],
        slow_mo=1000)

    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    user_email = get_user_email()

    # Step 1: Open expensify url
    page.goto('https://dev.new.expensify.com:8082/')

    # Step 2: Enter email and click continue
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()

    try:
        expect(page.get_by_role("button", name="Sign in")).to_be_visible()
        page.get_by_test_id("validateCode").fill(get_magic_code())
    except Exception:
        page.get_by_role("button", name="Join").click()

    return browser, page


# Test to verify that an empty thread is hidden in the LHN (Left-Hand Navigation)
def test_hide_thread():
    with sync_playwright() as p:
        # Step 1: Log in the user and complete onboarding
        browser, page = login_user(p)

        # Step 2: Perform actions to create a new thread in a Room
        page.get_by_label("Workspaces").click()

        page.get_by_label("Back").click()

        page.locator('div[data-testid="DisplayNamesWithTooltip"]',
                     has_text="#room").nth(0).click()

        # Step 4: Send a message to the room and create a thread
        page.get_by_role("textbox").fill("hey")

        page.locator('button[aria-label="Send"]').nth(-1).click()

        page.locator("div").filter(has_text=re.compile(
            r"^hey$")).nth(-1).click(button="right")

        page.get_by_text("Reply in thread").click()

        page.locator('div[data-testid="DisplayNamesWithTooltip"]',
                     has_text="#room").nth(0).click()

        # Step 5: Verify that the newly created thread is hidden if not commented on
        expect(page.locator('button[aria-label="Navigates to a chat"][role="button"][tabindex="0"]',
               # Ensure the thread is hidden if empty
                            has_text="No activity yet")).not_to_be_visible()

        # Step 6: Close the browser after the test is complete
        browser.close()
