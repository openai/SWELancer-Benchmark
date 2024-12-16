import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page
from playwright._impl._browser_context import BrowserContext

from utils.trace_cleaner import trace_cleaner

#### CONFIG

TEST_URL = "https://dev.new.expensify.com:8082/" 
USER_NAME = "expensify31" 
USER_PASSWORD = "Pass@123456" 

#### UTILS

def get_test_user_info(seed = None):
    if seed is None:
        return {"email": f"{USER_NAME}@gmail.com", "password": USER_PASSWORD, "first_name": f"{USER_NAME}", "last_name": "Test"}
    
    return {"email": f"{USER_NAME}+{seed}@gmail.com", "password": USER_PASSWORD, "first_name": f"Test", "last_name": "User"}

def wait(page, for_seconds=1):
    page.wait_for_timeout(for_seconds * 1000)

def login(p: PlaywrightContextManager, user_info, if_phone=False) -> tuple[Browser, Page, BrowserContext]:    
    permissions = ['clipboard-read', 'clipboard-write']
    browser = p.chromium.launch(headless=True,
                                args =[
            '--ignore-certificate-errors',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
        ])
    if if_phone:
        phone = p.devices['iPhone 12 Pro']
        context = browser.new_context(**phone, permissions=permissions, reduced_motion='no-preference')
    else:
        context = browser.new_context()

    page = context.new_page()

    page.goto(TEST_URL, timeout=120000) 
    phone_or_email_input = page.locator('input[type="email"]')
    expect(phone_or_email_input).to_be_visible()
    phone_or_email_input.fill(user_info["email"])

    continue_button = page.locator('button[tabindex="0"]')
    expect(continue_button).to_be_visible()
    continue_button.click()
    wait(page)

    join_button = page.locator('button:has-text("Join")')
    if join_button.count() > 0:
        print("Join button found. This is a new user.")
        join_button.click()
    else:
        print("Join button not found. This is an existing user. Use Magic Code to sign in.")
        magic_code = "123456" # for the mitmdump , since the code dosen't matter at this point of time
        print(f"Magic code: {magic_code}")

        validate_code_input = page.locator('input[data-testid="validateCode"]')
        expect(validate_code_input).to_be_visible()
        validate_code_input.fill(magic_code)
    return browser, page, context

def test_expensify_49894():
    with sync_playwright() as p:
        user_info = get_test_user_info(seed=76534345)
        browser, page, context = login(p, user_info, False)
        trace_path = "/app/expensify/user_tool/output_browser1.zip"

        try:
            context.tracing.start(screenshots=True, snapshots=True, sources=True)

            page.get_by_role("button", name="Create").click()
            page.get_by_label("Assign task").click()
            page.get_by_role("textbox", name="Title").fill("Test")
            page.get_by_role("textbox", name="Description (optional)").fill("`    `")
            page.get_by_role("button", name="Next").click()
            page.get_by_test_id("NewTaskPage").get_by_text("Description").click()
            page.get_by_role("textbox", name="Description (optional)").fill("`    ` ")
            page.get_by_role("button", name="Next").click()
            expect(page.get_by_test_id("code").locator("span")).to_be_visible()
        finally:
            # Stop tracing, export it, and clean it
            context.tracing.stop()
            context.tracing.export(path=trace_path)
            trace_cleaner(trace_path)
            browser.close()
