import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
import re
NEWDOT_URL = "https://dev.new.expensify.com:8082/"
OLDDOT_URL = "http://localhost:9000/"

def new_dot_login(page):
    page.goto(NEWDOT_URL)

def social_media_url(page, context):
    # Track if a new tab was opened
    new_tab_detected = False

    def handle_new_tab(new_page):
        nonlocal new_tab_detected
        new_tab_detected = True
        print("New tab detected with URL:", new_page.url)

    # Attach the listener
    context.on("page", handle_new_tab)

    # Click the element
    page.locator("a:nth-child(3)").hover()
    page.locator("a:nth-child(3)").click()

    # Allow time for the new tab to open
    page.wait_for_timeout(3000)  # Adjust this as needed

    # Check the flag
    if new_tab_detected:
        print("New tab was successfully opened.")
    else:
        print("No new tab was detected.")
        raise Exception("New tab was not opened as expected!")


def test_expensify_0000():
     with sync_playwright() as p:
        browser = p.chromium.launch(proxy = {"server": "http://localhost:8080"}, headless = False, args = ["--no-sandbox", "--disable-dev-shm-usage", "--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"], slow_mo = 1000, channel = "chromium")
        context = browser.new_context()
        page = context.new_page()
        new_dot_login(page)
        page.wait_for_timeout(2000)

        social_media_url(page,context)

        browser.close()