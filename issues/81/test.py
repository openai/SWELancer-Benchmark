from playwright.sync_api import sync_playwright
from urllib.parse import urlparse

def launch_browser(playwright):
    phone = playwright.devices["Galaxy S9+"]
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
    
    context = browser.new_context(timezone_id = "Asia/Karachi", **phone)
    page = context.new_page()

    return browser, page

def login_user(page, first_name="Test", last_name="User"):

    page.goto("https://dev.new.expensify.com:8082/")

    user_email = "freelancer.test.exp+1740087180@gmail.com"

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

        page.get_by_label("Back").click()
        page.get_by_label("My settings").click()
        page.get_by_label("Security").click()
        page.get_by_label("Add copilot").click()
        page.get_by_test_id("selection-list-text-input").fill("randomemail+53007@gmail.com")
        page.get_by_label("randomemail+53007@gmail.com").click()
        page.get_by_label("Full").click()
        page.get_by_role("button", name="Add copilot").click()
        page.go_back()
        
        confirm_path = urlparse(page.url).path.split('/')[-1]

        assert "confirm" == confirm_path

        browser.close()