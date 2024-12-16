import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page


# Utility to generate a random email
def generate_random_email():
    return f"turingtemp+826403@gmail.com"


def login_user(p: PlaywrightContextManager, first_name="Milan", last_name="T") -> tuple[Browser, Page, str]:
    # Launch chromiun and open new page
    browser = p.chromium.launch(headless=True, args=[
        "--disable-web-security",
        "--disable-features=IsolateOrigins,site-per-process"
    ])
    page = browser.new_page()
    user_email1 = generate_random_email()

    # Step 1: Open expensify url
    page.goto('https://dev.new.expensify.com:8082/')

    # Step 2: Enter email and click continue
    page.locator('input[type="email"]').fill(user_email1)
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(1000)

    # Step 3: Click join button
    try:
        page.locator('button[tabindex="0"]').click()
        page.wait_for_timeout(1000)
    except Exception:
        pass

    try:
        # Step 4: Select 'Track and budget expenses' in onobarding page and click Continue
        page.locator("text='Track and budget expenses'").click()
        page.get_by_role("button", name="Continue").click()
        page.wait_for_timeout(1000)

        # Step 5: Enter first name, last name and click continue
        page.locator('input[name="fname"]').fill(first_name)
        page.locator('input[name="lname"]').fill(last_name)
        page.get_by_role("button", name="Continue").last.click()
    except:
        pass

    page.wait_for_timeout(1000)
    return browser, page, user_email1


def test_save_description_in_submitted_expense(tmp_path):
    with sync_playwright() as p:
        browser, page, user_email = login_user(p)
        context = page.context
        context.tracing.start(screenshots=True, snapshots=True)
        try:
            page.wait_for_timeout(1000)
            page.locator('div[placeholder="Write something..."]').last.fill("yo!")
            page.wait_for_timeout(1000)
            page.keyboard.press("Enter")
            page.wait_for_timeout(1000)
            page.locator('div[aria-label="Chat message"]', has_text="yo!").last.click(button='right')
            page.wait_for_timeout(1000)
            page.locator(f'button[aria-label="👍"]').last.click()
            # go offline
            page.route('**/*', lambda route: route.abort())
            page.wait_for_timeout(3000)
            page.locator('div[aria-label="Chat message"]', has_text="yo!").last.click(button='right')
            page.wait_for_timeout(1000)
            page.locator(f'button[aria-label="😂"]').last.click()
            page.wait_for_timeout(1000)
            laugh_emoji_div = page.locator('div[class="css-view-175oi2r"][style="opacity: 0.5;"]', has_text="😂")
            page.wait_for_timeout(1000)
            expect(laugh_emoji_div).to_be_visible()
        except Exception:
            # Re-raise after any test failure, so the test is marked as failed
            raise
        finally:
            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            from utils.trace_cleaner import trace_cleaner
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            browser.close()
