import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from json import tool
import time
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page
from utils.trace_cleaner import trace_cleaner

static_email = "testuserexpensify1+44@gmail.com"


def login_user(p: PlaywrightContextManager, first_name="Milan", last_name="T") -> tuple[Browser, Page, str]:

    browser = p.chromium.launch(headless=True, slow_mo=1000, args=["--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"])
    page = browser.new_page()
    user_email = static_email

    page.goto('https://dev.new.expensify.com:8082/') 

    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(1000)

    try: 
        page.locator('button[tabindex="0"]').click() 
        page.wait_for_timeout(1000)
    except Exception:
        pass
        

    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()
    page.wait_for_timeout(1000)


    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()
    page.wait_for_timeout(1000)

    return browser, page, user_email


def test_close_account_bottom_margin():
    with sync_playwright() as p:
        first_name = 'John'
        last_name = 'Doe'
        new_workspace_name = 'Testing workspace'

        browser, page, user_email = login_user(p, first_name, last_name)
        context = browser.new_context()
        context.tracing.start(screenshots=True, snapshots=True, sources=True)

        try:
            profile = page.locator('button[aria-label="My settings"]')
            profile.click()
            page.wait_for_timeout(1000)
            
            troubleshoot = page.locator('div[role="menuitem"]').nth(9)
            troubleshoot.click()
            page.wait_for_timeout(1000)
            
            forced_offline = page.locator('button[aria-label="Force offline"]')
            forced_offline.click()
            page.wait_for_timeout(1000)
            
            plus_icon = page.locator('button[aria-label="Start chat (Floating action)"]')
            plus_icon.click()
            page.wait_for_timeout(2000)
            
            new_workspace_button = page.locator('div[aria-label="New workspace"]')
            new_workspace_button.click()
            page.wait_for_timeout(1000)
            
            workspace_name = f"{first_name} {last_name}'s Workspace"
            
            profile = page.locator(f'div[aria-label="{workspace_name}"]')
            profile.click()
            page.wait_for_timeout(1000)
            
            page.locator('input[aria-label="Name"]').fill(new_workspace_name)
            save_button = page.locator('button', has_text="Save")
            save_button.click()
            page.wait_for_timeout(1000)
            
            new_profile = page.locator(f'div[aria-label="{new_workspace_name}"]')
            page.wait_for_timeout(1000)
            
            profile_opacity = new_profile.evaluate(
                'element => window.getComputedStyle(element.parentElement.parentElement.parentElement.parentElement).opacity'
            )
            
            if profile_opacity == '0.5':
                assert True, 'Profile is grayed out.'
            else:
                assert False, 'Profile is not grayed out.'
                
            page.wait_for_timeout(1000)
        finally:
            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            browser.close()