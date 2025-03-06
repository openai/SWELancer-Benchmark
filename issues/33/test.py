import os
import time
import pytest
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page
from playwright.sync_api import sync_playwright, expect
import re, time
import os
import imaplib
import email
import re
import random
import numpy as np
import platform


NEWDOT_URL = "https://dev.new.expensify.com:8082/"
OLDDOT_URL = "http://localhost:9000/"
EMAIL = "test"+ str(random.randint(2234,78987))+"@yahoo.com"
PASSWORD = "uotx fzkt kfeg dehz"


def launch_browser(pw, headless=False, device=None, geolocation=None):
    """
    Launch the browser.
    """
    browser = pw.chromium.launch(headless=headless)
    context_args = {}
    if device:
        context_args.update(pw.devices[device])
    if geolocation:
        context_args["geolocation"] = geolocation
        context_args["permissions"] = ["geolocation"]
    context = browser.new_context(**context_args)
    page = context.new_page()
    return browser, context, page

def test_check_expense_title() -> None: 
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=[
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ],proxy={"server": "http://127.0.0.1:8080/"})

        first_user_context = browser.new_context(ignore_https_errors=True)
        page = first_user_context.new_page()     
        page.goto(NEWDOT_URL)  
        page.wait_for_timeout(3000)
        page.locator('input[type="email"]').fill(EMAIL)
        page.locator('button[tabindex="0"]').click()
        page.wait_for_timeout(1000)
        page.locator('button[tabindex="0"]').click() 
        page.wait_for_timeout(1000)
        expect(page.get_by_text("What do you want to do today? Track and budget expenses.simple-")).to_be_visible()
        
        page.wait_for_timeout(1500)
        page.close()
        browser.close()
