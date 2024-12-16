import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
import re
import time
import os
import imaplib
import email
import re
import random
import string
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
    otp = "123456"  # gmail_account_helper.check_for_otp()
    page.locator('input[data-testid="validateCode"]').fill(otp)


def room_members(page):
    page.wait_for_timeout(1000)
    page.get_by_label("Start chat (Floating action)").click()
    page.wait_for_timeout(1000)
    page.get_by_label("Start chat", exact=True).click()
    page.wait_for_timeout(1000)
    page.get_by_label("Room", exact=True).click()
    page.wait_for_timeout(1000)
    page.get_by_placeholder("social").click()
    page.wait_for_timeout(1000)
    page.get_by_placeholder("social").fill(f"social-13265")
    page.wait_for_timeout(1000)
    page.get_by_role("button", name="Create room").click()
    page.wait_for_timeout(1000)
    page.get_by_label(f"#social-13265").click()
    page.wait_for_timeout(1000)
    page.get_by_label("Members").click()
    page.wait_for_timeout(1000)
    try:
        assert page.get_by_test_id(
            "RoomMembersPage").get_by_label(EMAIL).is_visible()
    except Exception as err:
        assert page.get_by_test_id("RoomMembersPage").get_by_label(
            EMAIL).first.is_visible()

    page.get_by_role("button", name="Invite member").click()
    page.wait_for_timeout(1000)
    page.get_by_test_id("selection-list-text-input").click()
    page.wait_for_timeout(1000)
    page.get_by_test_id(
        "selection-list-text-input").fill("pehlajrajput1+8@gmail.com")
    page.wait_for_timeout(1000)
    page.locator("[id=\"\\31 8806886\"]").click()
    page.wait_for_timeout(1000)
    page.get_by_role("button", name="Invite").click()
    page.wait_for_timeout(3000)
    expect(page.locator("[id=\"\\31 8806886\"]")).to_be_visible()


def test_expensify_0000():

    with sync_playwright() as p:
        browser = p.chromium.launch(proxy={"server": "http://localhost:8080"}, headless=False, args=[
                                    "--no-sandbox", "--disable-dev-shm-usage", "--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"], slow_mo=1000, channel="chromium")
        context = browser.new_context()
        page = context.new_page()
        page.wait_for_timeout(2000)
        new_dot_login(page, EMAIL)
        page.wait_for_timeout(2000)
        room_members(page)
        browser.close()
