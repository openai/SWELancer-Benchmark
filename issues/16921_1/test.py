from email import message
from playwright.sync_api import sync_playwright, expect
import re, time
import os
import imaplib
import email
import re
import random
import string
NEWDOT_URL = "https://dev.new.expensify.com:8082/"
OLDDOT_URL = "http://localhost:9000/"
EMAIL = "pehlajrajput1@gmail.com"
PASSWORD = "vjycqezohxxrdhzr"

def new_dot_login(page, email):
    page.goto(NEWDOT_URL)
    page.locator('input[type="email"]').fill(email)
    page.wait_for_timeout(2000)
    page.get_by_role("button", name="Continue").nth(0).click()
    page.wait_for_timeout(10000)
    otp = "123456"
    page.locator('input[data-testid="validateCode"]').fill(otp)

def linebreak(page):
    # Step 1: Start the chat
    page.get_by_label("Start chat (Floating action)").click()
    page.wait_for_timeout(500)
    page.get_by_label("Start chat", exact=True).click()
    page.wait_for_timeout(2000)

    # Step 2: Fill in email and select it
    page.get_by_test_id("selection-list-text-input").click()
    page.wait_for_timeout(2000)
    page.get_by_test_id("selection-list-text-input").fill("pehlajrajput89@gmail.com")
    page.wait_for_timeout(1000)
    page.get_by_label("pehlajrajput89@gmail.com").click()
    page.wait_for_timeout(3000)

    # Step 3: Right-click on the report screen and edit comment
    page.get_by_test_id("report-screen-6050285816066334").get_by_test_id("html").click(button="right")
    page.wait_for_timeout(3000)
    page.get_by_label("Edit comment").click()
    page.wait_for_timeout(3000)

    # Step 4: Fill in the comment with "# hello..."
    page.get_by_test_id("report-screen-6050285816066334").get_by_test_id("report-actions-list").locator("#messageEditInput").fill(value="# hello...")
    page.wait_for_timeout(3000)
    page.get_by_label("Save changes").click()
    page.wait_for_timeout(3000)

    # Step 5: Triple-click on the "hello..." text to select it
    page.get_by_test_id("h1").get_by_text("hello...").click(click_count=3)
    page.wait_for_timeout(1000)

    # Step 6: Copy the selected text using Command/Control + C
    page.keyboard.press("ControlOrMeta+c")
    page.wait_for_timeout(4000)

    # Step 7: Paste the copied text into the composer
    composer_locator = page.locator('[contenteditable="true"]').last
    composer_locator.click()
    page.wait_for_timeout(4000)
    page.keyboard.press("ControlOrMeta+v")
    page.wait_for_timeout(4000)

    # Step 8: Verify that the text "# hello" is visible
    expect(composer_locator.get_by_text("# hello")).to_be_visible()


def test_expensify_0000():
     with sync_playwright() as p:
        browser = p.chromium.launch(proxy = {"server": "http://localhost:8080"}, headless = False, args = ["--no-sandbox", "--disable-dev-shm-usage", "--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"], slow_mo = 1000, channel = "chromium")
        context = browser.new_context()
        page = context.new_page()
        page.goto('https://dev.new.expensify.com:8082/') 
        page.wait_for_timeout(2000)
        new_dot_login(page, "pehlajrajput1@gmail.com")
        page.wait_for_timeout(2000)

        linebreak(page)

        browser.close()