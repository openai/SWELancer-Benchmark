import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
import pytest
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page


EMAIL = "t1533148@gmail.com"

def login_user(p: PlaywrightContextManager, first_name="AK", last_name="Test") -> tuple[Browser, Page, str]:
    # Launch chromiun and open new page
    browser = p.chromium.launch(channel='chrome', headless=True, slow_mo = 500,
            proxy = {"server": "http://127.0.0.1:8080/"},
            args=[
            "--ignore-certificate-errors",
            "--disable-web-security", 
            "--disable-features=IsolateOrigins,site-per-process"
        ])
    desktop = p.devices['Desktop Chrome']
    # desktop["viewport"] = {"width": 375, "height": 667}
    context = browser.new_context(**desktop)
    page = context.new_page()

    # Step 1: Open expensify url
    page.goto('https://127.0.0.1:8082/') 

    # Step 2: Enter email and click continue
    page.locator('input[type="email"]').fill(EMAIL)
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(1000)
    otp = '123456'
    page.locator('input[name="validateCode"]').first.click() # Focus
    page.keyboard.press('ArrowLeft');
    page.keyboard.press('ArrowLeft');
    page.wait_for_timeout(2000)
    page.keyboard.type(otp)
    page.wait_for_timeout(2000)
    try:
        page.locator("div").filter(has_text=re.compile(r"^Sign in$")).nth(-1).click()
        page.get_by_text("Concierge").last.wait_for()   
    except Exception:
        pass
    return browser, page

def test_the_issue():
    with sync_playwright() as p:
        browser, page = login_user(p)
        page.locator("text=Big Chat (Do Not Delete)").nth(0).click()
        page.get_by_label("Create").last.click()
        page.get_by_text("Assign task").click()
        page.get_by_role("textbox", name="Title").fill("asdaf")
        page.get_by_label("Description (optional)").locator("div").nth(3).click()
        page.get_by_role("textbox", name="Description (optional)").fill("`  `")
        page.get_by_role("button", name="Next").click()
        page.get_by_test_id("NewTaskPage").get_by_text("Description").click()

        page.get_by_role("textbox", name="Description (optional)").click()
        page.keyboard.press("End")  

        page.keyboard.type("  ")

        page.wait_for_timeout(1000)
        page.get_by_role("button", name="Next").click()
        code = page.locator('div[data-testid="code"]').last
        expect(code).to_be_visible()
        browser.close()