import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page

static_email = "expensify624+50@gmail.com"

def login_user(p: PlaywrightContextManager, first_name="Milan", last_name="T") -> tuple[Browser, Page, str]:
    # Launch chromiun and open new page
    browser = p.chromium.launch(headless=True, slow_mo=1000, args=["--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"])
    page = browser.new_page()
    user_email = static_email

    # Step 1: Open expensify url
    page.goto('https://dev.new.expensify.com:8082/') 

    # Step 2: Enter email and click continue
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()

    # Step 3: Click join button
    try:
        page.wait_for_timeout(1000)
        page.locator('button[tabindex="0"]').click()
    except Exception:
        pass
        
    # Step 4: Select 'Track and budget expenses' in onobarding page and click Continue
    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()

    # Step 5: Enter first name, last name and click continue
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()

    return browser, page, user_email


def test_the_issue():
    with sync_playwright() as p:
        browser, page, user_email = login_user(p)
        page.get_by_label("My settings").last.click()
        page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").get_by_text("Workspaces").click()
        page.get_by_label("New workspace").first.click()
        page.get_by_label("Back").last.click()
        page.locator('button[aria-label="Start chat (Floating action)"]').last.click()
        page.get_by_text("Start chat").last.click()
        page.keyboard.press("Shift+Tab")
        page.keyboard.press("Enter")

        page.get_by_placeholder("social").fill("sdfewf")
        page.locator('text="Create room"').last.click()
        page.keyboard.press("Enter")
        page.get_by_label("#sdfewf").last.click()
        page.get_by_text("Leave").last.click()
        page.get_by_text("Join").last.click()
        page.get_by_label("Send").last.click()
        page.get_by_label("#sdfewf").last.click()
        page.get_by_test_id("ReportDetailsPage").get_by_text("Settings").click()
        daily_0 = page.get_by_text("Daily").last
        expect(daily_0).to_be_visible()
        immediately = page.get_by_text("Immediately").last
        expect(immediately).not_to_be_visible()
