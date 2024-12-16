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
EMAIL = "pehlajrajput1+89@gmail.com"
PASSWORD = "vjycqezohxxrdhzr"

def new_dot_login(page, email):
    page.goto(NEWDOT_URL)
    page.locator('input[type="email"]').fill(email)
    page.wait_for_timeout(2000)
    page.get_by_role("button", name="Continue").nth(0).click()
    page.wait_for_timeout(10000)
    page.locator('input[data-testid="validateCode"]').fill("123456")

def timezone(page, context):
    page.get_by_label("My settings").click()
    page.wait_for_timeout(1000)
    page.get_by_label("Asia/Karachi").click()
    page.wait_for_timeout(1000)
    page.get_by_label("Automatically determine your").click()
    page.wait_for_timeout(1000)
    page.get_by_test_id("TimezoneInitialPage").get_by_label("Asia/Karachi").click()
    page.wait_for_timeout(1000)
    page.get_by_test_id("TimezoneSelectPage").get_by_label("Back").click()
    page.wait_for_timeout(1000)
    page.get_by_label("Automatically determine your").click()
    page.wait_for_timeout(1000)
    
    page1 = context.new_page()
    page1.goto("https://dev.new.expensify.com:8082/settings/profile/timezone/select")
    page.wait_for_timeout(2000)

    page1.get_by_label("Asia/Kamchatka").click()
    page.wait_for_timeout(2000)
    
    # Continue with further validations if necessary
    page1.get_by_label("Back").click()
    page.wait_for_timeout(2000)
    expect(page1.get_by_test_id("TimezoneInitialPage").get_by_label("Asia/Karachi")).to_be_visible()

    page1.get_by_label("Back").click()
    page.wait_for_timeout(2000)
    expect(page1.get_by_text("Asia/Karachi").first).to_be_visible()


def test_expensify_0000():
    with sync_playwright() as p:
        browser = p.chromium.launch(proxy = {"server": "http://localhost:8080"}, headless = False, args = ["--no-sandbox", "--disable-dev-shm-usage", "--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"], slow_mo = None, channel = "chromium")
        first_user_context = browser.new_context(ignore_https_errors=True, timezone_id="Asia/Karachi")
        first_user_context.tracing.start(screenshots=True, snapshots=True, sources=True)
        try:
            page = first_user_context.new_page()
            page.wait_for_timeout(2000)
            new_dot_login(page, "pehlajrajput1@gmail.com")
            page.wait_for_timeout(2000)

            timezone(page, first_user_context)
        finally:
            first_user_context.tracing.stop()
            first_user_context.tracing.export_trace("/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            browser.close()
