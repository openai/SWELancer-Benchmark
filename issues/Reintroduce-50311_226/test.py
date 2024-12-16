import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from playwright._impl._page import Page
from playwright._impl._errors import TimeoutError

# Constants for delay times in milliseconds
ONE_SECOND = 1000
TWO_SECONDS = 2000
# Expensify app URL
NEWDOT_URL = "https://dev.new.expensify.com:8082/"
EMAIL = "adebayovicktor0+tests50311@gmail.com"


def new_dot_login(page: Page, email_account: str):
    page.goto(NEWDOT_URL)
    page.locator('input[type="email"]').fill(email_account)
    page.wait_for_timeout(2000)
    page.locator("div:nth-child(3) > div:nth-child(2) > div > div").first.click()
    # Wait for OTP
    page.wait_for_timeout(1000)
    otp = '123456'
    page.locator('input[name="validateCode"]').first.click() # Focus
    page.keyboard.press('ArrowLeft')
    page.keyboard.press('ArrowLeft')
    page.keyboard.type(otp)
    try:
        page.locator("div").filter(has_text=re.compile(r"^Sign in$")).nth(1).click()
    except:
        pass
    page.get_by_text("Concierge").last.wait_for()

def check_if_searched_item_is_in_search_result(page: Page):
    amount = str(1000)
    number = "+1 6317918379"
    getter = "+1 631-791-"
    page.get_by_label("Start chat (Floating action)").click()
    page.get_by_label("Submit expense").first.click()
    page.get_by_label("Manual").click()
    page.get_by_placeholder("0").fill(amount)
    page.locator("#numPadContainerView").get_by_role("button", name="Next").click()
    page.get_by_test_id("selection-list-text-input").fill(number)
    page.get_by_label(getter).click()
    # page.get_by_role("button", name="Submit NGN").click()
    page.get_by_role("button", name="Submit").click()
    page.wait_for_timeout(TWO_SECONDS)
    expect(page.get_by_text("Unexpected error creating")).to_be_visible(timeout=TWO_SECONDS)
    page.get_by_label("Close").click()
    page.wait_for_timeout(TWO_SECONDS)
    page.get_by_label("Start chat (Floating action)").click()
    expect(page.get_by_role("menuitem").nth(3)).not_to_be_visible(timeout=TWO_SECONDS)
    expect(page.get_by_role("menuitem").nth(4)).not_to_be_visible(timeout=TWO_SECONDS)

def run_test(page: Page):
    """run the assertion"""
    check_if_searched_item_is_in_search_result(page)

def test_expensify_50311():
    """main test run"""
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True, args=["--ignore-certificate-errors", '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
            '--proxy-server=http://localhost:8080',]
        )
        context_args = {}
        context_args["geolocation"] = {"latitude": 37.7749, "longitude": 122.4194}
        context_args["permissions"] = ["geolocation"]
        context_args["ignore_https_errors"] = True
        first_user_context = browser.new_context(**context_args)
        first_user_page = first_user_context.new_page()
        new_dot_login(first_user_page, EMAIL)
        run_test(first_user_page)
        first_user_context.close()
        browser.close()
