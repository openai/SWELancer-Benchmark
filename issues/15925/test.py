import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

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
EMAIL = "pehlajrajput1+89@gmail.com"
PASSWORD = "vjycqezohxxrdhzr"

def new_dot_login(page, email):
    page.goto(NEWDOT_URL)
    page.locator('input[type="email"]').fill(email)
    page.wait_for_timeout(2000)
    page.get_by_role("button", name="Continue").nth(0).click()
    page.wait_for_timeout(10000)
    page.locator('input[data-testid="validateCode"]').fill("123456")

def line_break(page):
    page.get_by_label("Start chat (Floating action)").click()
    page.wait_for_timeout(1000)
    page.get_by_label("Start chat", exact=True).click()
    page.wait_for_timeout(1000)
    page.get_by_test_id("selection-list-text-input").click()
    page.wait_for_timeout(1000)
    page.get_by_test_id("selection-list-text-input").fill("pehlajrajput1+34@gmail.com")
    page.wait_for_timeout(1000)
    page.get_by_test_id("selection-list").get_by_label("pehlajrajput1+34@gmail.com").click()
    page.wait_for_timeout(1000)
    page.get_by_test_id("report-actions-list").get_by_text("a b c").click(click_count=3)
    page.wait_for_timeout(1000)
    page.keyboard.press("Shift+ArrowDown")
    page.keyboard.press("Shift+ArrowDown")
    page.keyboard.press("ControlOrMeta+c")
    page.wait_for_timeout(1000)
    composer_locator = page.locator('[contenteditable="true"]').last
    composer_locator.click()
    page.wait_for_timeout(1000)
    page.keyboard.press("ControlOrMeta+v")
    page.wait_for_timeout(1000)

    # Retrieve the actual text and print it for debugging
    actual_text = composer_locator.evaluate("el => el.innerText")
    print(f"Actual text in composer: {repr(actual_text)}")

    # Validate against the expected text
    expected_text = "a\n\nb\n\nc"
    assert actual_text == expected_text, f"Expected '{expected_text}', but got '{actual_text}'"


def test_expensify_0000():

     with sync_playwright() as p:
        browser = p.chromium.launch(proxy = {"server": "http://localhost:8080"}, headless = False, args = ["--no-sandbox", "--disable-dev-shm-usage", "--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"], slow_mo = None, channel = "chromium")
        first_user_context = browser.new_context(ignore_https_errors=True)
        page = first_user_context.new_page()
        page.wait_for_timeout(2000)
        new_dot_login(page, "pehlajrajput1+89@gmail.com")
        page.wait_for_timeout(2000)
        line_break(page)
        browser.close()