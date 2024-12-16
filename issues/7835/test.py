import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from playwright._impl._page import Page
# import re
# import time
# import imaplib
# import email
# import random
# from typing import Any


NEWDOT_URL = "https://dev.new.expensify.com:8082/"
OLDDOT_URL = "http://localhost:9000/"
EMAIL = "pehlajrajput1+345@gmail.com"
PASSWORD = "vjycqezohxxrdhzr"


def new_dot_login(page, email) -> None:
    page.locator('input[type="email"]').fill(email)
    page.wait_for_timeout(2000)
    page.get_by_role("button", name="Continue").nth(0).click()
    page.wait_for_timeout(10000)
    # email_handle = EmailHandler(email, PASSWORD)
    otp = "123456"
    page.locator('input[data-testid="validateCode"]').fill(otp)


def video_preview(page: Page) -> None:
    page.get_by_label("Start chat (Floating action)").click()
    page.wait_for_timeout(2000)
    page.get_by_label("Start chat", exact=True).click()
    page.wait_for_timeout(2000)
    page.get_by_test_id("selection-list-text-input").click()
    page.wait_for_timeout(2000)
    page.get_by_test_id("selection-list-text-input").fill("pehlajrajput1+89@gmail.com")
    page.get_by_text("pehlajrajput1+89@gmail.com").last.click()
    page.wait_for_timeout(3000)
    video_selector = page.get_by_role("button", name="w_6aec9dba1ab4c14f1b7bb6c6e6f66fad1182b8eb.webm")
    expect(video_selector).to_be_visible()
    page.wait_for_timeout(3000)
    video_selector.click()
    page.wait_for_timeout(2000)
    # try:
    page.evaluate("""
        const video = Array.from(document.querySelectorAll('video'));
        if (video.at(-1)) {
            video.at(-1).play();
        } else {
            throw new Error(video);
        }
    """)

    # Verify the video is playing
    is_paused = page.evaluate("""
    () => {
        const video = Array.from(document.querySelectorAll('video')).at(-1);
        return video ? video.paused : true;
    }
    """)
    assert not is_paused, "Video is paused or not playing"


def test_expensify_0000() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(
            proxy = {"server": "http://localhost:8080"}, headless = False, args = ["--no-sandbox", "--disable-dev-shm-usage", "--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"], slow_mo = 1000, channel = "chromium")
        context = browser.new_context(
            ignore_https_errors=True
            )
        page = context.new_page()
        # page.pause()
        page.goto('https://dev.new.expensify.com:8082/')
        page.wait_for_timeout(2000)
        new_dot_login(page, "pehlajrajput1+345@gmail.com")
        page.wait_for_timeout(5000)

        video_preview(page)
        browser.close()
