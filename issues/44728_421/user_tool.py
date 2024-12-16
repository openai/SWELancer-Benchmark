import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page

static_email = "testuserexpensify1+63@gmail.com"

def login_user(p: PlaywrightContextManager, first_name="John", last_name="Doe") -> tuple[Browser, Page, str]:

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
        page.locator('button[tabindex="0"]').click() 
    except Exception:
        pass

    # Step 4: Select 'Track and budget expenses' in onboarding page and click Continue
    page.locator("text='Something else'").click()
    page.get_by_role("button", name="Continue").click()

    # Step 5: Enter first name, last name and click continue
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()
  
    return browser, page, user_email

def test_44728():
    with sync_playwright() as p:
        browser, page, user_email = login_user(p)
        page.context.tracing.start(title="test_44728", screenshots=True, snapshots=True)
        try:
            personal_chat = page.get_by_text(f"(you)")
            personal_chat.click()

            # Locate the "Concierge" chat text element
            concierge_text = page.locator('text=Concierge').nth(1)

            # Get the font-weight of the text element to check if it's bold
            font_weight = concierge_text.evaluate("el => window.getComputedStyle(el).fontWeight")
            # Check if font-weight is equal or greater than 700 (bold text)
            assert int(font_weight) >= 700, "The Concierge chat is not marked as unread."
        finally:
            page.context.tracing.stop()
            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            page.context.tracing.export(path=trace_path)
            from utils.trace_cleaner import trace_cleaner
            trace_cleaner(trace_path)
            browser.close()
