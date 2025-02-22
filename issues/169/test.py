import re
from playwright.sync_api import sync_playwright, expect

def launch_browser(playwright):
    browser = playwright.chromium.launch(
            channel="chrome",
            headless=False,
            slow_mo=500,
            proxy={"server": "http://localhost:8080"},
            args=[
                "--ignore-certificate-errors",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process"
            ]
        )
    
    context = browser.new_context(timezone_id = "Asia/Karachi")
    page = context.new_page()

    return browser, page

def login_user(page, first_name="Test", last_name="User"):

    page.goto("https://dev.new.expensify.com:8082/")

    user_email = "freelancer.test.exp+1739715118@gmail.com"

    page.get_by_test_id("username").fill(user_email)
    page.get_by_role("button", name="Continue").click()
    page.get_by_role("button", name="Join").click()
    page.get_by_text("Track and budget expenses").click()
    page.get_by_role("button", name="Continue").click()
    page.get_by_role("textbox", name="First name").fill(first_name)
    page.get_by_role("textbox", name="Last name").fill(last_name)
    page.get_by_role("form").get_by_role("button", name="Continue").click()


def test_example():
    with sync_playwright() as playwright:

        browser, page = launch_browser(playwright)
        login_user(page)

        tracking_header = re.compile("Tracking .+")

        page.get_by_test_id("lhn-options-list").get_by_text("Test User (you)").first.click()
        page.get_by_role("button", name="Create").click()
        page.get_by_label("Track expense").click()
        page.get_by_label("Manual").click()
        page.get_by_placeholder("0").fill("100")
        page.locator("#numPadContainerView").get_by_role("button", name="Next").click()
        page.get_by_role("button", name="Track expense").click()
        page.get_by_text("Cash").click()
        page.get_by_label(tracking_header).first.click()

        expect(page.get_by_label("Submit it to someone")).to_be_visible()
        expect(page.get_by_label("Categorize it")).to_be_visible()
        expect(page.get_by_label("Share it with my accountant")).to_be_visible()
        
        browser.close()