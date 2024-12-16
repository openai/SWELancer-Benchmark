import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import Playwright, sync_playwright, expect
from playwright._impl._browser import Browser
from playwright._impl._page import Page

from utils.trace_cleaner import trace_cleaner

# Utility to generate a random email
def generate_random_email():
    return f"srkiitd+44259d@gmail.com"


def login_user(p: Playwright, first_name="John", last_name="Doe") -> tuple[Browser, Page, str]:
    browser = p.chromium.launch(channel="chrome", headless=True, args=[
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ])

    page = browser.new_page()

    user_email = generate_random_email()

    # Step 1: Open expensify url
    page.goto('https://dev.new.expensify.com:8082/') 

    # Step 2: Enter email and click continue
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(1000)

    # Step 3: Click join button
    try: 
        page.locator('button[tabindex="0"]').click() 
        page.wait_for_timeout(1000)
    except Exception:
        pass
    page.wait_for_timeout(5000)
    # Step 4: Select 'Track and budget expenses' in onboarding page and click Continue
    try:
        page.locator("text='Track and budget expenses'").click()
        page.get_by_role("button", name="Continue").click()
        page.wait_for_timeout(1000)

        # Step 5: Enter first name, last name and click continue
        page.locator('input[name="fname"]').fill(first_name)
        page.locator('input[name="lname"]').fill(last_name)
        page.get_by_role("button", name="Continue").last.click()
        page.wait_for_timeout(1000)
    except Exception:
        pass

    return browser, page, user_email


def test_44259():
    with sync_playwright() as p:
        trace_path = "/app/expensify/user_tool/output_browser1.zip"
        browser = None
        page = None
        try:
            browser, page, user_email = login_user(p)
            # Start recording the trace after the browser and page are created
            page.context.tracing.start(screenshots=True, snapshots=True, sources=True)

            personal_chat = page.get_by_text(f"(you)")
            expect(personal_chat).to_be_visible()
            personal_chat.click()
            page.wait_for_timeout(1000)

            message = "Hello my friend"
            message_box = page.get_by_role("textbox")
            message_box.fill(message)
            page.wait_for_timeout(1000)

            # Refresh the page
            page.reload()
            page.wait_for_timeout(10000)
            refreshed_message_box = page.get_by_role("textbox")
            cursor_position = refreshed_message_box.evaluate("el => window.getSelection().anchorOffset")

            assert cursor_position == len(message), f"Expected cursor position {len(message)}, but got {cursor_position}"

        except Exception as e:
            # Stop and clean trace on failure
            if page:
                page.context.tracing.stop(path=trace_path)
                trace_cleaner(trace_path)
            if browser:
                browser.close()
            raise e
        else:
            # Stop and clean trace on success
            page.context.tracing.stop(path=trace_path)
            trace_cleaner(trace_path)
            if browser:
                browser.close()
