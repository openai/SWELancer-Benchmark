from pydoc import cli
from playwright.sync_api import sync_playwright, expect
import re, time
import os
import imaplib
import email
import re
import random
import string

# import the cleaner
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

def formatting(page):
    page.get_by_label("Start chat (Floating action)").click()
    page.wait_for_timeout(2000)
    page.get_by_label("Start chat", exact=True).click()
    page.wait_for_timeout(2000)
    page.get_by_test_id("selection-list-text-input").click()
    page.wait_for_timeout(2000)
    page.get_by_test_id("selection-list-text-input").fill("pehlajrajput1+43@gmail.com")
    page.get_by_test_id("selection-list").get_by_label("pehlajrajput1+43@gmail.com").click()
    page.wait_for_timeout(2000)
    page.get_by_text("<html> <body> <h1>HTML").click(button="right")
    page.wait_for_timeout(1000)
    page.get_by_label("Copy to clipboard").click()
    page.wait_for_timeout(2000)
    page.get_by_test_id("report-screen-8198893088087890").locator("#composer")
    page.wait_for_timeout(2000)
    page.keyboard.press("ControlOrMeta+v")
    page.wait_for_timeout(2000)
    expect(page.get_by_text("<html><body> <h1>HTML")).to_be_visible()


def test_expensify_0000():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="chrome",
            headless=False,
            args=[
                "--ignore-certificate-errors",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
            ]
        )
        first_user_context = browser.new_context(ignore_https_errors=True)
        # Start tracing
        first_user_context.tracing.start(
            title="test_expensify_0000",
            screenshots=True,
            snapshots=True,
            sources=True
        )

        page = first_user_context.new_page()
        page.wait_for_timeout(2000)

        try:
            new_dot_login(page, "pehlajrajput1+89@gmail.com")
            page.wait_for_timeout(2000)
            formatting(page)
        except Exception as e:
            print(f"An error occurred: {e}")
            raise
        finally:
            # Stop tracing and export
            first_user_context.tracing.stop()
            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            first_user_context.tracing.export(trace_path)

            # Clean the trace
            trace_cleaner(trace_path)

            browser.close()
