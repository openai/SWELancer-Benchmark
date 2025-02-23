import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
import re, time
import imaplib
import email
from playwright._impl._browser import Browser
from playwright._impl._page import Page
import random


user_email = "totherandomuser+005@gmail.com"
password = "umei djwi bfmp jntm"
EMAIL = "totherandomuser+005@gmail.com"
PASSWORD = "umei djwi bfmp jntm"
NEWDOT_URL = "https://dev.new.expensify.com:8082"

def new_dot_login(page, email):
    page.goto(NEWDOT_URL)
    page.locator('input[type="email"]').fill(email)
    page.wait_for_timeout(2000)
    page.get_by_role("button", name="Continue").nth(0).click()
    page.wait_for_timeout(10000)
    otp = "123456"
    page.locator('input[data-testid="validateCode"]').fill(otp)


def login(p):
    browser = p.chromium.launch(proxy = {"server": "http://localhost:8080"}, headless = False, args = ["--no-sandbox", "--disable-dev-shm-usage", "--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"], slow_mo = 1000, channel = "chromium")

    context = browser.new_context()

    page = context.new_page()

    page.goto('https://dev.new.expensify.com:8082/') 

    new_dot_login(page, user_email)

    return browser, page, context


def test():
    with sync_playwright() as p:
        browser, page, context = login(p)
        page.wait_for_timeout(5000)
        page.get_by_label("Start chat (Floating action)").click()
        page.wait_for_timeout(1000)
        page.get_by_label("Start chat", exact=True).click()
        page.wait_for_timeout(1000)
        page.get_by_test_id("selection-list-text-input").fill("testuseracc22@gmail.com")
        page.wait_for_timeout(2000)
        page.get_by_test_id("selection-list").get_by_label("testuseracc22@gmail.com").click()
        page.wait_for_timeout(3000)
        page.keyboard.press("ControlOrMeta+j")
        page.wait_for_timeout(1000)
        expect(page.get_by_text("Save time with these handy keyboard shortcuts:")).to_be_visible()
        context.close()
        browser.close()
