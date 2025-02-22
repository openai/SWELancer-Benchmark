import time
from playwright.sync_api import sync_playwright, expect
from utils.email_handler import get_unique_derived_email, EmailHandler

GMAIL_NAME = "testerbro7077@gmail.com"
GMAIL_APP_PASSWORD = "xqxz mmcb tvkn lpgp"

def login_member_a(p, membera_first_name: str, membera_last_name: str) -> tuple:
    browser = p.chromium.launch(
        proxy = {"server": "http://localhost:8080"}, headless = False, args = ["--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"], slow_mo = 1100, channel = "chromium")
    context = browser.new_context()
    page = context.new_page()

    # Generate a unique email using the base Gmail address
    user_email2 = "testerbro7077+usera134@gmail.com"

    page.goto('https://dev.new.expensify.com:8082/')
    page.locator('input[type="email"]').fill(user_email2)
    page.get_by_role("button", name="Continue").click()
    page.wait_for_timeout(1000)

    try:
        page.get_by_role("button", name="Join").click()
        page.wait_for_timeout(1000)
    except Exception:
        pass

    expect(page.locator("text=What do you want to do today?")).to_be_visible()
    page.wait_for_timeout(1000)
    page.get_by_text("Track and budget expenses").click()

    page.locator('input[name="fname"]').fill(membera_first_name)
    page.locator('input[name="lname"]').fill(membera_last_name)
    page.get_by_role("button", name="Continue").last.click()
    page.wait_for_timeout(1000)

    return browser, page, user_email2

def check_ws_navigation(page):
    user_email2 = "testerbro7077+userb134@gmail.com"

    page.get_by_label("Start chat (Floating action)").click()
    try:
        page.get_by_text("Create expense").click()
    except:
        page.get_by_text("Submit expense").click()
    page.get_by_label("Manual").click()
    page.get_by_placeholder("0").fill("100")
    page.locator("#numPadContainerView").get_by_role("button", name="Next").click()
    
    page.get_by_test_id("selection-list-text-input").fill(user_email2)
    page.get_by_label(user_email2).click()
    page.get_by_role("button", name="Submit $").click()
    
    page.get_by_label("My settings").click()
    page.get_by_text("Sign out").click()
    page.wait_for_timeout(3000)
    page.get_by_test_id("username").fill(user_email2)
    page.get_by_role("button", name="Continue").click()
    
    page.wait_for_timeout(3000)
    page.get_by_test_id("validateCode").fill("123456")
    
    page.locator('button[aria-label="Navigates to a chat"]').nth(1).click()
    page.get_by_role("button", name="Pay $100.00 with Expensify").click()
    page.get_by_text("Business bank account").click()
    page.get_by_label("Back").click()
    page.locator('button[aria-label="Navigates to a chat"]').nth(0).click()
    page.get_by_text("Set up categories").nth(0).click()
    page.get_by_text("Take me to workspace category").click()
    current_url = page.url
    assert "-1" not in current_url, "Workspace Id not present in the URL"
    assert page.get_by_test_id("WorkspaceCategoriesPage").get_by_text("Categories", exact=True).is_visible(), "Categories page not visible"

def test_run(membera_first_name="Sai", membera_last_name="Yagna"):
    with sync_playwright() as p:
        browser_membera, page_membera, user_email2 = login_member_a(p, membera_first_name, membera_last_name)
        check_ws_navigation(page_membera)
        browser_membera.close()

if __name__ == "__main__":
    test_run()
