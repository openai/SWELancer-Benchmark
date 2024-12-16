import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import pytest
from playwright.sync_api import sync_playwright, expect
from utils.trace_cleaner import trace_cleaner

@pytest.fixture(scope="function")
def page():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, slow_mo=500, args=[
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
            '--proxy-server=http://localhost:8080',
        ])
        context = browser.new_context()
        page = context.new_page()
        yield page
        context.close()
        browser.close()


def test_room_chat_lhn_preview(page):
    trace_path = "/app/expensify/user_tool/output_browser1.zip"
    page.context.tracing.start(screenshots=True, snapshots=True, sources=True)

    try:
        page.goto('https://dev.new.expensify.com:8082/')
        suffix = 54332
        phone_or_email_input = page.locator('input[type="email"]')
        expect(phone_or_email_input).to_be_visible()
        phone_or_email_input.fill(f"expensify624+{suffix}@gmail.com")

        continue_button = page.locator('button[tabindex="0"]')
        expect(continue_button).to_be_visible()
        continue_button.click()
        page.wait_for_timeout(1000)

        try:
            continue_button = page.locator('button[tabindex="0"]')
            expect(continue_button).to_be_visible()
            continue_button.click()
        except Exception as e:
            pytest.fail(f"Test failed: {str(e)}")

        expect(page.locator("text='Track and budget expenses'")).to_be_visible()
        page.locator("text='Track and budget expenses'").click()
        page.get_by_role('button', name='Continue').click()

        page.locator('input[aria-label="First name"]').fill("Test")
        page.locator('input[aria-label="Last name"]').fill("Name")
        page.get_by_role("form").get_by_role("button", name="Continue").click()
        page.get_by_role('button', name='Get Started').click()

        settings = page.get_by_label("My settings")
        expect(settings).to_be_visible()
        settings.click()

        page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").get_by_text("Workspaces").click()
        page.get_by_label("New workspace").first.click()
        page.get_by_label("Back").click()
        page.get_by_label("Inbox").click()

        admin_channel = page.get_by_test_id('lhn-options-list').get_by_text("#admins")
        expect(admin_channel).to_be_visible()
        admin_channel.click()
        page.wait_for_timeout(2000)

        page.get_by_role('button', name='#admin').click()
        page.get_by_text('Room description').click()
        page.locator('div[role="textbox"][aria-label="Room description"]').fill('LHN room preview test')
        page.get_by_role('button', name='Save').click()
        page.mouse.click(0, 0)
        page.wait_for_timeout(2000)

        expect(page.get_by_text('removed 0 user')).not_to_be_visible(timeout=1)

    finally:
        page.context.tracing.stop(path=trace_path)
        trace_cleaner(trace_path)
