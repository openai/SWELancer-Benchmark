import imaplib
import email
import re
from playwright.sync_api import sync_playwright, expect, Page


EMAIL = "velmoner+375@gmail.com"
PASSWORD = "aory ezrb qkmi qkas"
NEWDOT_URL = "https://dev.new.expensify.com:8082/"

def user_login(page: Page, email_id: str, password: str):
    page.goto(NEWDOT_URL)

    page.locator('input[type="email"]').fill(email_id)
    page.wait_for_timeout(2000)
    page.get_by_role("button", name="Continue").nth(0).click()
    otp = "123456"
    page.locator('input[data-testid="validateCode"]').fill(otp)
    try:
        page.get_by_role("button", name="Sign In").click()
    except Exception as err:
        pass


def test_payment_text():
    with sync_playwright() as p:
        browser = p.chromium.launch(proxy = {"server": "http://localhost:8080"}, headless = False, args = ["--no-sandbox", "--disable-dev-shm-usage", "--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"], slow_mo = 1000, channel = "chromium")
        page = browser.new_page()

        user_login(page=page, email_id=EMAIL, password=PASSWORD)

        page.get_by_label("workspaces").click()

        if page.get_by_role("button", name="Get Started").is_visible():
            page.get_by_role("button", name="Get Started").click()
            page.get_by_label("Back").click()
            page.get_by_label("Inbox").click()
            page.get_by_label("workspaces").click()

        assert not page.get_by_test_id("WorkspaceSwitcherPage").get_by_label(
            "New workspace").is_visible()

        # Close browser
        browser.close()

