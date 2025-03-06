import time

from playwright.sync_api import Page, expect, sync_playwright


# Utility to generate a random email
def generate_random_email(timestamp):
    return f"openaipg+{timestamp}@gmail.com"


def create_user(
    page: Page, firstname: str, lastname: str = None, timestamp: int = None
):
    timestamp = timestamp
    # Sign up
    page.get_by_test_id("username").fill(generate_random_email(timestamp))
    page.get_by_role("button", name="Continue").click()
    page.get_by_role("button", name="Join").click()

    # Update profile
    page.get_by_text("Track and budget expenses").click()
    page.get_by_role("textbox", name="First name").fill(firstname)
    page.get_by_role("textbox", name="Last name").fill(
        lastname or f"{timestamp}")
    page.get_by_role("button", name="Continue").click()


def test_download_button_snackbar():

    with sync_playwright() as p:
        timestamp = 1740041211

        # Launch chromium and open new page
        browser = p.chromium.launch(proxy = {"server": "http://localhost:8080"}, headless = False, args = ["--no-sandbox", "--disable-dev-shm-usage", "--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"], slow_mo = 1000, channel = "chromium")
        context = browser.new_context()
        page = context.new_page()

        page.goto("https://dev.new.expensify.com:8082/")

        # create user
        create_user(page, "TestUser", f"{timestamp}", timestamp)

        page.goto("https://dev.new.expensify.com:8082/statements/202404")

        # Test Download
        page.get_by_label("Download").click()

        # In fixed state, Snackbar with given text should not appear
        expect(page.get_by_text("We're generating your PDF")).not_to_be_visible()

        # ---------------------
        context.close()
        browser.close()
