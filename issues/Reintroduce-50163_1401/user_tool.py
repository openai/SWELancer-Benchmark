import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import os
from typing import Any
from playwright.sync_api import sync_playwright, expect
from playwright._impl._page import Page

from utils.trace_cleaner import trace_cleaner

email_address = "brighturing926+50163@gmail.com"


def launch_browser(platform='desktop') -> tuple[Any, Any, Page]:
    """
    Launch a persistent browser with the specified platform
    """

    playwright = sync_playwright().start()
    data_dir = 'mobile_context' if platform.lower() == 'mobile' else 'browser_context'
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    mobile_context = {}

    if platform.lower() == 'mobile':
        mobile_context = {
            # Pixel 8 viewport
            'viewport': {'width': 412, 'height': 915},
            'is_mobile': True,
            'user_agent': "Chrome/129.0.0.0"
        }

    context = playwright.chromium.launch_persistent_context(
        data_dir,
        headless=True,
        **mobile_context,
        args=[
            "--disable-web-security",
            "--disable-features=Isolateorigins,aite-per-process"
        ]
    )

    # persistent context already has the page
    page = context.pages[0]

    return playwright, context, page


def login_user_if_not_logged_in(page: Page, email: str, platform="chromium") -> None:
    # Launch chromiun and open new page

    # Step 1: Open expensify url
    page.goto('https://dev.new.expensify.com:8082/')

    page.wait_for_load_state('load')

    try:
        # If the user is already logged in, the inbox should be visible
        expect(page.get_by_label("Inbox")).to_be_visible(timeout=3000)
        return
    except Exception:
        pass

    # Step 3: Enter email and click continue
    page.locator('input[type="email"]').fill(email)
    page.locator('button', has_text="Continue").click()

    page.get_by_test_id("validateCode").fill("123456")

    # Step 3: Click join button
    try:
        page.get_by_role("button", name="Sign in").click()

    except Exception:
        pass

    # Step 7: Wait for the onboarding process to complete,
    # this can be crucial to avoid any flakiness in the test
    # For Narrow layout, open the chat for Track an expense
    if platform.lower() == 'mobile':
        page.get_by_label('Last chat message preview').filter(has_text='task for Track an expense').wait_for()
        page.get_by_label('Last chat message preview').filter(has_text='task for Track an expense').click()
    # page.get_by_label("guided-setup-track-personal-").wait_for()
    # For Narrow layout, click on Back button to navigate to inbox
    if platform.lower() == 'mobile':
        page.get_by_label("Back").click()
        page.get_by_label("Inbox").wait_for()


def test_clear_search() -> None:
    """
    Demonstrate that the user session is persisted
    """

    platform = "desktop"
    playwright, context, page = launch_browser(platform)

    # Start tracing
    context.tracing.start(screenshots=True, snapshots=True)

    try:
        email = email_address

        # Step 2: Login to expensify
        login_user_if_not_logged_in(page, email, platform)

        # Step 3: click on the search and input demo search text
        page.get_by_label("Search").nth(1).click()
        page.get_by_test_id("search-router-text-input").fill("demo")
        page.get_by_label("demo").click()

        # Step 4: Click on filters and save the search term
        page.get_by_role("button", name="Filters").click()
        page.get_by_role("button", name="Save search").click()

        # Step 5: Click on more option in the added search term the rename
        page.get_by_label("More").first.click()
        page.get_by_label("Rename").click()

        # Step 6: Check if the clear button is visible
        expect(page.get_by_label("Clear")).to_be_visible()

    finally:
        # Stop tracing and save to file
        context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
        trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
        context.close()
        playwright.stop()
