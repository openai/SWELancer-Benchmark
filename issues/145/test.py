import time
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page

# Utility to generate a random email
def generate_random_email():
    return "testerbro7077+453457745684@gmail.com"

# Login as member and fill in personal details
def login_member_a(p, membera_first_name: str, membera_last_name: str) -> tuple:
    browser = p.chromium.launch(
        proxy = {"server": "http://localhost:8080"}, headless = False, 
        args = ["--ignore-certificate-errors", 
                "--disable-web-security", 
                "--disable-features=IsolateOrigins,site-per-process"], 
        slow_mo = 500, channel = "chromium")
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()


    user_email2 = generate_random_email()

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

# Add the member to the workspace using `user_email2`
def auto_sueestion_check(page, user_email2):
    page.locator('button[aria-label="Navigates to a chat"]').nth(1).click()
    page.get_by_label("Search").get_by_role("img").nth(1).click()
    page.get_by_test_id("search-router-text-input").fill("in:Co")
    page.get_by_label("in:Concierge").click()
    assert not page.get_by_role("button", name="in:Concierge").nth(1).is_visible(), "Suggestion visible even after it is selected"


def test_run(membera_first_name="Sai", membera_last_name="Yagna"):
    with sync_playwright() as p:

        browser_membera, page_membera, user_email2 = login_member_a(p, membera_first_name, membera_last_name)
        auto_sueestion_check(page_membera, user_email2)

        

        browser_membera.close()


if __name__ == "__main__":
    test_run()