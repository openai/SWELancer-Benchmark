import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page

from utils.trace_cleaner import trace_cleaner

# Gmail credentials for generating user info
GMAIL_NAME = "milan.thummar"
GMAIL_APP_PASSWORD = "example_password"  # Replace with actual app password if needed

# Utility to generate user info
def get_test_user_info(seed=None, first_name=None, last_name=None):
    if first_name is None:
        first_name = GMAIL_NAME.split(".")[0].capitalize()
    if last_name is None:
        last_name = ""
    email = f"{GMAIL_NAME}+{seed}@gmail.com" if seed is not None else f"{GMAIL_NAME}@gmail.com"
    return {"email": email, "password": GMAIL_APP_PASSWORD, "first_name": first_name, "last_name": last_name}


def login_user(p: PlaywrightContextManager, first_name="Milan", last_name="T") -> tuple[Browser, Page, str]:
    # Launch Chromium and open a new page
    browser = p.chromium.launch(channel="chromium", slow_mo=2000, headless=True, args=[
        "--disable-web-security",
        "--disable-features=IsolateOrigins,site-per-process",
        "--ignore-certificate-errors",
    ])
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    user_info = get_test_user_info(seed=int(time.time()), first_name=first_name, last_name=last_name)
    user_email = user_info["email"]

    # Step 1: Open expensify url
    page.goto('https://dev.new.expensify.com:8082/')

    # Step 2: Enter email and click continue
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(2000)

    # Step 3: Click join button
    try:
        page.locator('button[tabindex="0"]').click()
        page.wait_for_timeout(2000)
    except Exception:
        pass
    expect(page.locator("text=What do you want to do today?")).to_be_visible()

    # Step 4: Select 'Track and budget expenses' in onobarding page and click Continue
    try:
        page.locator("text='Track and budget expenses'").click()
        page.get_by_role("button", name="Continue").click()

        # Step 5: Enter first name, last name and click continue
        page.locator('input[name="fname"]').fill(first_name)
        page.locator('input[name="lname"]').fill(last_name)
        page.get_by_role("button", name="Continue").last.click()
        page.wait_for_timeout(2000)
    except Exception:
        pass

    return browser, page, context, user_email


def test_emojiart():
    with sync_playwright() as p:
        browser, page, context, user_email = login_user(p)
        # Start recording trace
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        try:
            # Step 2: Start a chat and send emojiart
            page.get_by_label("Start chat (Floating action)").click()
            page.get_by_text("Start chat").click()
            page.get_by_test_id("selection-list").get_by_label("Concierge").click()
            page.get_by_role("textbox").fill("💙💗💗💗💗💗💗\n💙❤❤❤❤❤  💛💗\n💙❤HELLO ♪❤💛💗\n💙❤👍☀👎❤ 💛💗\n💙❤☮ O˥˥ƎH❤💛💗\n💙❤❤❤❤❤   💛💗\n💚💚💚💚💚💚💛\n")
            page.keyboard.press("Enter")

            # Step 3: open emoji picker
            page.get_by_label("Emoji").click()
            page.wait_for_timeout(2000)

            # Assert that the emoji picker is visible
            expect(page.get_by_text("Frequently Used").first).to_be_visible(), "Emoji picker fails to open, app crashes."
        except Exception as e:
            raise e
        finally:
            # Stop recording trace and export
            context.tracing.stop()
            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            context.tracing.export(trace_path)
            trace_cleaner(trace_path)
