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
from utils.trace_cleaner import trace_cleaner

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
    page.locator('input[data-testid="validateCode"]').fill("123456")

def emoji_popover(page):
    page.get_by_label("Start chat (Floating action)").click()
    page.wait_for_timeout(1000)
    page.get_by_label("Start chat", exact=True).click()
    page.wait_for_timeout(1000)
    page.get_by_test_id("selection-list-text-input").click()
    page.wait_for_timeout(1000)
    page.get_by_test_id("selection-list-text-input").fill("toanynewuser@gmail.com")
    page.wait_for_timeout(1000)
    page.get_by_label("toanynewuser@gmail.com").click()
    page.wait_for_timeout(1000)
    current_url = page.url


    match = re.search(r"/r/(\d+)", current_url)
    if match:
        last_id = match.group(1)
        print(f"Extracted last ID: {last_id}")
        

        test_id = f"report-screen-{last_id}"
        page.get_by_test_id(test_id).get_by_label("Emoji").click()
    else:
        print("No matching ID found in the URL.")
    page.wait_for_timeout(1000)
    page.get_by_label("emojiPicker.headers.travelAndPlaces").hover(timeout = 1000)
    page.wait_for_timeout(1000)
    expect(page.get_by_text("Travel & Places")).to_be_visible()

def test_expensify_0000():
     with sync_playwright() as p:
        browser = p.chromium.launch(proxy = {"server": "http://localhost:8080"}, headless = False, args = ["--no-sandbox", "--disable-dev-shm-usage", "--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"], slow_mo = 1000, channel = "chromium")
        context = browser.new_context()
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        page = context.new_page()
        try:
            page.wait_for_timeout(2000)
            new_dot_login(page, "pehlajrajput1@gmail.com")
            page.wait_for_timeout(2000)
            emoji_popover(page)
        finally:
            context.tracing.stop()
            context.tracing.export_trace("/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            browser.close()
