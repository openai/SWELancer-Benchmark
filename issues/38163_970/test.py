import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)


import time
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page
from playwright._impl._browser_context import BrowserContext


def test_anonymous_user():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=[
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ])
        context = browser.new_context()
        page = context.new_page()
        
        page.goto('https://dev.new.expensify.com:8082/r/3295647304331553') 

        page.get_by_text('https://dev.new.expensify.com:8082/settings/security').click()

        # Check that the text does not exist
        enable_2fa = page.get_by_text("Enable two-factor authentication to keep your account safe.")
        expect(enable_2fa).not_to_be_visible()
   
