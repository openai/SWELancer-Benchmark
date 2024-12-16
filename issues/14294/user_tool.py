import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from pydoc import cli
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
EMAIL = "pehlajrajput1+345@gmail.com"
PASSWORD = "vjycqezohxxrdhzr"

def new_dot_login(page, email):
    page.goto(NEWDOT_URL)
    page.locator('input[type="email"]').fill(email)
    page.wait_for_timeout(2000)
    page.get_by_role("button", name="Continue").nth(0).click()
    page.wait_for_timeout(10000)
    otp = "123456"
    page.locator('input[data-testid="validateCode"]').fill(otp)


def composer_formatting(page):
    page.get_by_label("Start chat (Floating action)").click()
    page.wait_for_timeout(1000)
    page.get_by_label("Start chat").last.click()
    page.wait_for_timeout(1000)
    page.get_by_test_id("selection-list-text-input").click()
    page.wait_for_timeout(1000)
    page.get_by_test_id("selection-list-text-input").fill("pehlajrajput1+34@gmail.com")
    page.get_by_label("pehlajrajput1+34@gmail.com").click()
    page.wait_for_timeout(1000)

    # Use the existing context from the page
    context = page.context
    page1 = context.new_page()
    page1.goto("https://docs.google.com/document/d/1Et76Q96542J5flZNAFddAsoAAqNUQpff8XdQ1eUXagE/edit?usp=sharing")
    page1.wait_for_timeout(1000)
    page1.keyboard.press("ControlOrMeta+a")
    page1.wait_for_timeout(1000)
    page1.keyboard.press("ControlOrMeta+c")
    page1.close()

    page.wait_for_timeout(1000)
    page.get_by_test_id("report-screen-233899578988683").locator("#composer")
    page.wait_for_timeout(1000)
    page.keyboard.press("ControlOrMeta+v")
    page.wait_for_timeout(1000)
    page.keyboard.press("Enter")
    page.wait_for_timeout(1000)

    # Assert that there are no asterisks or bold markers
    normal = page.get_by_text("Normal", exact=False).last

    assert '*' not in normal.text_content(), "Single asterisk (*) is present in the 'normal' element"

    context = page.context
    page1 = context.new_page()
    page1.goto("https://docs.google.com/document/d/1zWxUmaJyFga3cLG5IW7fAlOmbq1IxT8mI-c83vXRkCI/edit?tab=t.0")
    page1.wait_for_timeout(1000)
    page1.keyboard.press("ControlOrMeta+a")
    page1.wait_for_timeout(1000)
    page1.keyboard.press("ControlOrMeta+c")
    page1.close()

    page.wait_for_timeout(1000)
    page.get_by_test_id("report-screen-233899578988683").locator("#composer")
    page.wait_for_timeout(1000)
    page.keyboard.press("ControlOrMeta+v")
    page.wait_for_timeout(1000)
    page.keyboard.press("Enter")
    page.wait_for_timeout(1000)

    # Assert that there are no asterisks or bold markers
    bold = page.get_by_text("Bold", exact=False).last

    assert '**' not in bold.text_content(), "Single asterisk (*) is present in the 'normal' element"


def test_expensify_0000():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=False, args=[
        "--ignore-certificate-errors",
        "--disable-web-security",
        "--disable-features=IsolateOrigins,site-per-process"],)
        first_user_context = browser.new_context(ignore_https_errors=True)

        first_user_context.tracing.start(screenshots=True, snapshots=True, sources=True)

        try:
            page = first_user_context.new_page()
            page.wait_for_timeout(2000)
            new_dot_login(page, "pehlajrajput1+345@gmail.com")
            page.wait_for_timeout(2000)
            composer_formatting(page)
        finally:
            first_user_context.tracing.stop()
            first_user_context.tracing.export_trace("/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            browser.close()
