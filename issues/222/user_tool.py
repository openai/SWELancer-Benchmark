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
EMAIL = "pehlajrajput1+34@gmail.com"
PASSWORD = "vjycqezohxxrdhzr"


def new_dot_login(page, email):
    page.goto(NEWDOT_URL)
    page.locator('input[type="email"]').fill(email)
    page.wait_for_timeout(2000)
    page.get_by_role("button", name="Continue").nth(0).click()
    page.wait_for_timeout(10000)
    page.locator('input[data-testid="validateCode"]').fill("123456")


def create_workspace(page):
    page.get_by_label("My settings").click()
    page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()
    page.get_by_label("New workspace").click()
    page.get_by_label("Back").click()


def emoji_size(page):
    page.get_by_label("Start chat (Floating action)").click()
    page.wait_for_timeout(1000)
    page.get_by_label("Start chat", exact=True).click()
    page.wait_for_timeout(1000)
    page.get_by_test_id("selection-list-text-input").click()
    page.get_by_test_id("selection-list-text-input").fill("pehlajrajput34@gmail.com")
    page.wait_for_timeout(1000)
    page.get_by_label("pehlajrajput34@gmail.com").click()
    page.wait_for_timeout(1000)
    page.locator("div").filter(has_text=re.compile(r"^Heyy$")).nth(4).click()
    page.get_by_label(":joy:").click()
    emoji_locator = page.locator("div").filter(has_text=re.compile(r"^😂1$")).nth(3)
    page.wait_for_timeout(1000)
    emoji_box = emoji_locator.bounding_box()
    print(f"Emoji Size - Width: {emoji_box['width']} px, Height: {emoji_box['height']} px")
    

    assert 26 <= emoji_box['width'] <= 45, f"Emoji width should be around 28px, but was {emoji_box['width']}px"
    assert 26 <= emoji_box['height'] <= 45, f"Emoji height should be around 28px, but was {emoji_box['height']}px"


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


        context.tracing.start(title="test_expensify_0000", snapshots=True, screenshots=True)

        page = context.new_page()
        try:
            page.goto('https://dev.new.expensify.com:8082/')
            page.wait_for_timeout(2000)
            new_dot_login(page, "pehlajrajput1+34@gmail.com")
            page.wait_for_timeout(2000)
            emoji_size(page)
        except Exception as e:
            print(f"Test failed: {e}")
        finally:

            context.tracing.stop()
            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            context.tracing.export(path=trace_path)
            trace_cleaner(trace_path)
            browser.close()
