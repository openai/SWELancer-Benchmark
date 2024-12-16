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
from pathlib import Path

NEWDOT_URL = "https://dev.new.expensify.com:8082/"
OLDDOT_URL = "http://localhost:9000/"
EMAIL = "pehlajrajput1+345@gmail.com"
PASSWORD = "vjycqezohxxrdhzr"

def new_dot_login(page, email_id):
    page.goto(NEWDOT_URL)
    page.locator('input[type="email"]').fill(email_id)
    page.wait_for_timeout(2000)
    page.get_by_role("button", name="Continue").nth(0).click()
    page.wait_for_timeout(10000)
    page.locator('input[data-testid="validateCode"]').fill("123456")


def multiple_tabs_logout(page, context):
    page.get_by_label("Start chat (Floating action)").click()
    page.wait_for_timeout(1000)
    page.get_by_label("Start chat", exact=True).click()
    page.wait_for_timeout(1000)
    page.get_by_test_id("selection-list-text-input").click()
    page.wait_for_timeout(1000)
    page.get_by_test_id("selection-list-text-input").fill("pehlajrajput1+89@gmail.com")
    page.wait_for_timeout(1000)
    page.get_by_label("pehlajrajput1+89@gmail.com").click()
    page.wait_for_timeout(1000)
    page1 = context.new_page()
    page1.goto("https://dev.new.expensify.com:8082/r/653157407532449")
    page1.wait_for_timeout(1000)
    page1.get_by_label("My settings").click()
    page1.wait_for_timeout(1000)
    page1.get_by_label("Sign out").click()
    page1.wait_for_timeout(1000)
    expect(page1.get_by_label("Sign out")).not_to_be_visible()

    page.bring_to_front()
    expect(page.get_by_text("Another login page is open.")).to_be_visible()
    
def test_expensify_0000():
    with sync_playwright() as p:
        browser = p.chromium.launch(proxy = {"server": "http://localhost:8080"}, headless = False, args = ["--no-sandbox", "--disable-dev-shm-usage", "--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"], slow_mo = 1000, channel = "chromium")
        first_user_context = browser.new_context()
        page = first_user_context.new_page()
        page.wait_for_timeout(2000)
        new_dot_login(page, "pehlajrajput1+345@gmail.com")
        page.wait_for_timeout(2000)

        multiple_tabs_logout(page, first_user_context)
        browser.close()