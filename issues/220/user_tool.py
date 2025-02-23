import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from this import d
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
EMAIL = "pehlajrajput1+4@gmail.com"
PASSWORD = "vjycqezohxxrdhzr"


def new_dot_login(page, email):
    page.goto(NEWDOT_URL)
    page.locator('input[type="email"]').fill(email)
    page.wait_for_timeout(2000)
    page.get_by_role("button", name="Continue").nth(0).click()
    page.wait_for_timeout(10000)
    page.locator('input[data-testid="validateCode"]').fill("123456")


def detect_flicker_using_stability(page):

    page.get_by_label("My settings").click()
    page.get_by_role("menuitem", name="Date of birth").click()
    page.get_by_label("3", exact=True).locator("div").first.click()


    element = page.get_by_role("menuitem", name="Date of birth")


    initial_box = element.bounding_box()
    if not initial_box:
        raise AssertionError("Initial bounding box is not available.")


    flicker_count = 0


    for _ in range(10):  # Check 10 times in the next 1 second
        current_box = element.bounding_box()
        if not current_box:
            raise AssertionError("Bounding box is not available during flicker check.")


        if (current_box['x'] != initial_box['x'] or
            current_box['y'] != initial_box['y'] or
            current_box['width'] != initial_box['width'] or
            current_box['height'] != initial_box['height']):
            flicker_count += 1


        initial_box = current_box

        page.wait_for_timeout(100)  # Wait for 100ms between checks


    if flicker_count > 2:
        raise AssertionError("Flickering detected due to rapid bounding box changes.")
    else:
        print("No flickering detected.")


def test_expensify_0000():
    with sync_playwright() as p:
        browser = p.chromium.launch(proxy = {"server": "http://localhost:8080"}, headless = False, args = ["--no-sandbox", "--disable-dev-shm-usage", "--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"], slow_mo = 1000, channel = "chromium")
        context = browser.new_context()
        context.tracing.start(screenshots=True, snapshots=True, sources=True)

        try:
            page = context.new_page()
            page.goto('https://dev.new.expensify.com:8082/')
            page.wait_for_timeout(2000)
            new_dot_login(page, "pehlajrajput1+4@gmail.com")
            page.wait_for_timeout(2000)


            detect_flicker_using_stability(page)
        finally:
            context.tracing.stop()
            context.tracing.export_trace("/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            browser.close()
