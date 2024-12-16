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

def emoji_malfunction(page, context):
    page.get_by_label("Start chat (Floating action)").click()
    page.wait_for_timeout(1000)
    page.get_by_label("Start chat", exact=True).click()
    page.wait_for_timeout(1000)
    page.get_by_test_id("selection-list-text-input").click()
    page.wait_for_timeout(1000)
    page.get_by_test_id("selection-list-text-input").fill("pehlajrajput1+43@gmail.com")
    page.wait_for_timeout(1000)
    page.get_by_test_id("selection-list").get_by_label("pehlajrajput1+43@gmail.com").click()
    page.wait_for_timeout(1000)
    composer_locator = page.locator('[contenteditable="true"]').last
    composer_locator.click()
    composer_locator.type("Te😄 st")
    page.wait_for_timeout(1000)
    composer_locator.press("ArrowLeft")
    page.wait_for_timeout(1000)
    composer_locator.press("ArrowLeft")
    page.wait_for_timeout(1000)
    page.get_by_label("Emoji").last.click()
    page.wait_for_timeout(1000)
    page.get_by_label("😉").click()
    page.wait_for_timeout(1000)
    expect(page.get_by_text("undefinedst")).not_to_be_visible()


def test_expensify_0000():
     with sync_playwright() as p:
        browser = p.chromium.launch(proxy = {"server": "http://localhost:8080"}, headless = False, args = ["--no-sandbox", "--disable-dev-shm-usage", "--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"], slow_mo = None, channel = "chromium")        
        first_user_context = browser.new_context(ignore_https_errors=True)
        page = first_user_context.new_page()
        page.wait_for_timeout(2000)
        new_dot_login(page, "pehlajrajput1+89@gmail.com")
        page.wait_for_timeout(2000)

        emoji_malfunction(page, first_user_context)

        browser.close()