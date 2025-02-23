from email import message
from playwright.sync_api import sync_playwright, expect
import re, time
import os
import imaplib
import email
import re
import random
import string
import traceback
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

def linebreak(page):

    page.get_by_label("Start chat (Floating action)").click()
    page.wait_for_timeout(500)
    page.get_by_label("Start chat", exact=True).click()
    page.wait_for_timeout(2000)


    page.get_by_test_id("selection-list-text-input").click()
    page.wait_for_timeout(2000)
    page.get_by_test_id("selection-list-text-input").fill("pehlajrajput89@gmail.com")
    page.wait_for_timeout(1000)
    page.get_by_label("pehlajrajput89@gmail.com").click()
    page.wait_for_timeout(3000)


    page.get_by_test_id("report-screen-6050285816066334").get_by_test_id("html").click(button="right")
    page.wait_for_timeout(3000)
    page.get_by_label("Edit comment").click()
    page.wait_for_timeout(3000)


    page.get_by_test_id("report-screen-6050285816066334").get_by_test_id("report-actions-list").locator("#messageEditInput").fill(value="# hello...")
    page.wait_for_timeout(3000)
    page.get_by_label("Save changes").click()
    page.wait_for_timeout(3000)


    page.get_by_test_id("h1").get_by_text("hello...").click(click_count=3)
    page.wait_for_timeout(1000)


    page.keyboard.press("ControlOrMeta+c")
    page.wait_for_timeout(4000)


    composer_locator = page.locator('[contenteditable="true"]').last
    composer_locator.click()
    page.wait_for_timeout(4000)
    page.keyboard.press("ControlOrMeta+v")
    page.wait_for_timeout(4000)


    expect(composer_locator.get_by_text("# hello")).to_be_visible()


def test_expensify_0000():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            proxy = {"server": "http://localhost:8080"},
            headless = False,
            args = ["--no-sandbox", "--disable-dev-shm-usage", "--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"],
            slow_mo = 1000,
            channel = "chromium"
        )
        context = browser.new_context()


        context.tracing.start(title="trace", screenshots=True, snapshots=True, sources=True)
        page = context.new_page()
        
        try:
            page.goto('https://dev.new.expensify.com:8082/')
            page.wait_for_timeout(2000)
            new_dot_login(page, "pehlajrajput1@gmail.com")
            page.wait_for_timeout(2000)
            linebreak(page)
        except Exception as e:

            raise e
        finally:

            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            browser.close()
