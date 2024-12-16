import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import os
from playwright.sync_api import sync_playwright, expect
from playwright._impl._page import Page
from utils.trace_cleaner import trace_cleaner

TIMEOUT = 20000
NEWDOT_URL = "https://dev.new.expensify.com:8082/"
TEST_EMAIL = "osaidtest5@gmail.com"

def launch_browser(platform="desktop"):
    """
    Launch a persistent browser with the specified platform
    """
    playwright = sync_playwright().start()
    data_dir = "mobile_context" if platform.lower() == "mobile" else "browser_context"
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    mobile_context = {}

    if platform.lower() == "mobile":
        mobile_context = {
            # Pixel 8 viewport
            "viewport": {"width": 412, "height": 915},
            "is_mobile": True,
            "user_agent": "Chrome/129.0.0.0",
        }

    context = playwright.chromium.launch_persistent_context(
        data_dir, headless=True,
        proxy={
            'server': 'http://127.0.0.1:8080',
        },
        args=[
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
        ], **mobile_context, slow_mo=2000
    )
    context.set_default_navigation_timeout(TIMEOUT)
    context.set_default_timeout(TIMEOUT)

    # persistent context already has the page
    page = context.pages[0]
    return playwright, context, page


def login_user_if_not_logged_in(page: Page):
    # Step 1: Open expensify url
    page.goto(NEWDOT_URL)
    page.wait_for_load_state("load")

    try:
        # If the user is already logged in, the inbox should be visible
        expect(page.get_by_label("Inbox")).to_be_visible(timeout=5000)
        return
    except:
        pass

    # Step 2: Enter email and click continue
    page.locator('input[type="email"]').fill(TEST_EMAIL)
    page.get_by_role("button", name="Continue").click()
    page.wait_for_timeout(5000)
    otp_code = "123456"
    page.keyboard.type(otp_code)


def test_correct_invoice_amount_displayed_after_currency_change():
    playwright, context, page = launch_browser()

    # Start Playwright tracing
    context.tracing.start(screenshots=True, snapshots=True, sources=True)
    trace_path = "/app/expensify/user_tool/output_browser1.zip"

    try:
        login_user_if_not_logged_in(page)

        # Generate an invoice.
        fab_button = page.locator('button[aria-label="Start chat (Floating action)"]')
        fab_button.click()
        page.get_by_text("Send invoice").click()
        page.get_by_placeholder("0").fill("100")
        page.get_by_role("button", name="Next").click()
        page.get_by_test_id("selection-list-text-input").fill("osaidtest5+1@gmail.com")
        page.get_by_role("button", name="fdsa fdsa", exact=True).click()
        page.get_by_role("button", name="100.00 invoice").click()
        page.wait_for_timeout(3000)

        # Go to the previously generated invoice's detail page.
        page.get_by_role('button', name="View details").filter(has=page.get_by_text("100.00")).last.click()
        page.get_by_role("menuitem",name="100.00").click()
        page.get_by_label("Select a currency").click()
        # Select a currency that is not the workspace's default.
        page.get_by_label("AED - Dhs").first.click()
        page.get_by_role("button", name="Save").click()
        total = page.get_by_text('fdsa fdsa owes PKR 0.00').last
        page.wait_for_timeout(4000)
        expect(total).not_to_be_visible()

    except Exception as e:
        print(f"Error occurred during test: {e}")
        raise

    finally:
        # Stop tracing and export
        context.tracing.stop()
        context.tracing.export(trace_path)
        trace_cleaner(trace_path)
        context.close()
        playwright.stop()
