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
    otp = "123456"
    page.locator('input[data-testid="validateCode"]').fill(otp)


def compose_box(page):
    page.get_by_label("Start chat (Floating action)").click()
    page.wait_for_timeout(2000)
    page.get_by_label("Start chat", exact=True).click()
    page.wait_for_timeout(2000)
    page.get_by_test_id("selection-list-text-input").click()
    page.wait_for_timeout(2000)
    page.get_by_test_id("selection-list-text-input").fill("agata.kosior@callstack.com")
    page.wait_for_timeout(2000)
    page.get_by_test_id("selection-list").get_by_label("Agata Kosior").click()
    page.wait_for_timeout(2000)
    composer_locator = page.locator('[contenteditable="true"]').last
    composer_locator.type("Hi")
    page.wait_for_timeout(1000)
    expect(composer_locator.get_by_text("Hi", exact=True)).to_be_visible()


def test_expensify_0000():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            proxy={"server": "http://localhost:8080"},
            headless=False,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"],
            slow_mo=1000,
            channel="chromium"
        )
        context = browser.new_context()

        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        page = context.new_page()
        try:
            page.goto('https://dev.new.expensify.com:8082/')
            page.wait_for_timeout(2000)
            new_dot_login(page, "pehlajrajput1@gmail.com")
            page.wait_for_timeout(2000)
            compose_box(page)
        except Exception as e:
            print(f"Test failed with exception: {e}")
            raise
        finally:

            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")

            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            browser.close()
