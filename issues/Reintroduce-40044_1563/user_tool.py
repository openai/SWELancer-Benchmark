import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect, Browser, BrowserContext, Page
from playwright.sync_api._context_manager import PlaywrightContextManager
from utils.trace_cleaner import trace_cleaner

EXPENSIFY = 'https://dev.new.expensify.com:8082/'


def launch_browser(p: PlaywrightContextManager) -> tuple[Browser, Page]:
    """
        Launches a new browser and opens a new page
    """
    browser = p.chromium.launch(channel='msedge', headless=True, args=["--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"])
    context = browser.new_context()
    page = context.new_page()

    return browser, context, page


def duplicate_tab(context: BrowserContext, page_a: Page):
    """
        duplicates a given tab (page)
    """
    storage_state = context.storage_state()
    
    page_b = context.new_page()
    page_b.goto(page_a.url)
    context.add_cookies(storage_state['cookies'])
    
    return page_b


def check_login_form_visible(page: Page):
    """
        Checks if login form is visible
    """
    email_field = page.locator('input[aria-label="Phone or email"][type="email"]')
    expect(email_field).to_be_visible()


def check_another_tab_message(page: Page):
    """
        Checks the message saying another login tab is open
    """
    message = page.locator('form', has_text="Another login page is open.")
    expect(message).to_be_visible()


def close_page(page: Page):
    """
        Closes a given page in playwright
    """
    page.evaluate("window.dispatchEvent(new Event('beforeunload'))")
    page.close()


def test_lead_status_transfer():
    """
        Tests if the lead status is correctly transferred when a tab is closed
    """
    with sync_playwright() as p:
        browser, context, page_a = launch_browser(p)
        # Start tracing before doing any actions
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        try:
            page_a.goto(EXPENSIFY)
            check_login_form_visible(page_a)

            page_b = duplicate_tab(context, page_a)

            page_a.bring_to_front()
            check_another_tab_message(page_a)

            close_page(page_b)
            check_login_form_visible(page_a)
        except Exception as e:
            # Re-raise the exception after ensuring we can capture the trace
            raise e
        finally:
            # Stop tracing and export the trace
            context.tracing.stop()
            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            context.tracing.export(path=trace_path)
            # Clean the trace
            trace_cleaner(trace_path)
            
            browser.close()
