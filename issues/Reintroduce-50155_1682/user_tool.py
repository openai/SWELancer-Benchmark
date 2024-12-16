import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from playwright._impl._browser import Browser
from playwright._impl._page import Page
from playwright.sync_api._context_manager import PlaywrightContextManager

from utils.trace_cleaner import trace_cleaner

# Utility to generate a random email
def generate_random_email():
    timestamp = 12210
    return f"newtestuser+{timestamp}@gmail.com"


def login_user(p: PlaywrightContextManager, first_name="Milan", last_name="T") -> tuple[Browser, Page, str]:
    # Launch chromiun and open new page
    browser = p.chromium.launch(headless=True, args=[
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
        ])
    page = browser.new_page()
    user_email = generate_random_email()

    # Step 1: Open expensify url
    page.goto('https://dev.new.expensify.com:8082/')

    # Step 2: Enter email and click continue
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(2000)

    # Step 3: Click join button
    try:
        page.locator('button[tabindex="0"]').click()
        page.wait_for_timeout(4000)
    except Exception:
        pass
    try:
        # Step 4: Select 'Track and budget expenses' in onobarding page and click Continue
        page.locator("text='Track and budget expenses'").click()
        page.get_by_role("button", name="Continue").click()
        page.wait_for_timeout(2000)

        # Step 5: Enter first name, last name and click continue
        page.locator('input[name="fname"]').fill(first_name)
        page.locator('input[name="lname"]').fill(last_name)
        page.get_by_role("button", name="Continue").last.click()
        page.wait_for_timeout(2000)
    except:
        pass

    return browser, page, user_email


def test_select_country_book_travel():
    """
    Demonstrate the Expensify app email login verification for mobile web.
    """
    with sync_playwright() as pw:
        browser, page, user_email = login_user(pw)
        trace_path = "/app/expensify/user_tool/output_browser1.zip"

        # Start tracing
        page.context.tracing.start(screenshots=True, snapshots=True, sources=True)
        try:
            page.get_by_test_id("CustomBottomTabNavigator").get_by_label("Search").click()
            page.locator("div:nth-child(4) > div > div > div > div > div > div > div > div:nth-child(2)").first.click()
            page.get_by_role("button", name="Book a trip").click()
            page.get_by_role("menuitem", name="Country").click()
            page.locator("#overLayBottomButton").click()
            page.wait_for_timeout(1000)
            expect(page.get_by_text("Use Expensify Travel to get")).to_be_visible()
        except Exception as e:
            # Re-raise to fail the test while still allowing us to stop tracing
            raise e
        finally:
            # Stop trace and clean it up
            page.context.tracing.stop(path=trace_path)
            trace_cleaner(trace_path)
            browser.close()


if __name__ == "__main__":
    test_select_country_book_travel()
