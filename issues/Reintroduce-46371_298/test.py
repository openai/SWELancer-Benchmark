import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import pytest
from playwright.sync_api import sync_playwright, expect
import time


def generate_random_email():
    timestamp = int(time.time())
    return f"freelanceapptest+{timestamp}@gmail.com"

# USER_EMAIL = generate_random_email()
USER_EMAIL = "freelanceapptest+728@gmail.com"

@pytest.fixture(scope="function")
def page():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="chrome",
            headless=True,
            args=[
                "--ignore-certificate-errors",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process"
            ],
            proxy={"server": "http://localhost:8080"},
            slow_mo=500
        )
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        yield page
        browser.close()


def test_check_unhold_button_exists(page):
    first_name = 'Test'
    last_name = 'Name'
    workspace_name = f"{first_name} {last_name}'s Workspace"

    page.goto('https://dev.new.expensify.com:8082/')
    phone_or_email_input = page.locator('input[type="email"]')
    expect(phone_or_email_input).to_be_visible()
    phone_or_email_input.fill(USER_EMAIL)

    continue_button = page.locator('button[tabindex="0"]')
    expect(continue_button).to_be_visible()
    continue_button.click()
    time.sleep(1)

    try:
        continue_button = page.locator('button[tabindex="0"]')
        expect(continue_button).to_be_visible()
        continue_button.click()
    except Exception as e:
        pytest.fail(f"Test failed: {str(e)}")

    expect(page.locator("text='Track and budget expenses'")).to_be_visible()
    page.locator("text='Track and budget expenses'").click()

    page.locator('input[aria-label="First name"]').fill(first_name)
    page.locator('input[aria-label="Last name"]').fill(last_name)
    page.locator('button[data-listener="Enter"]').click()

    settings = page.locator('button[aria-label="My settings"]')
    expect(settings).to_be_visible()
    settings.click()

    # Create workspace
    page.locator('div[aria-label="Workspaces"]').click()
    page.locator('button[aria-label="New workspace"]').first.click()
    page.locator('text="More features"').click()
    page.locator('button[aria-label="Document and reclaim eligible taxes."]').click()
    page.get_by_label("Back").click()
    page.get_by_label("Inbox").click()

    # Select created workspace
    workspace = page.get_by_test_id('lhn-options-list').get_by_text(workspace_name).first
    expect(workspace).to_be_visible()
    workspace.click()

    # Submit expense number 1
    page.get_by_role("button", name="Create").click()
    page.get_by_label("Submit expense").get_by_text("Submit expense").click()
    page.get_by_label("Manual").click()
    page.get_by_placeholder("0").fill("111")
    page.locator("#numPadContainerView").get_by_role("button", name="Next").click()
    page.get_by_test_id("selection-list").get_by_text("Merchant").click()
    page.get_by_role("textbox", name="Merchant").fill("merchant1")
    page.get_by_role("button", name="Save").click()
    page.get_by_role("button", name="Submit").click()

    # Submit expense number 2
    page.get_by_role("button", name="Create").click()
    page.get_by_label("Submit expense").get_by_text("Submit expense").click()
    page.get_by_label("Manual").click()
    page.get_by_placeholder("0").fill("222")
    page.locator("#numPadContainerView").get_by_role("button", name="Next").click()
    page.get_by_test_id("selection-list").get_by_text("Merchant").click()
    page.get_by_role("textbox", name="Merchant").fill("merchant2")
    page.get_by_role("button", name="Save").click()
    page.get_by_role("button", name="Submit").click()

    # Submit expense number 3
    page.get_by_role("button", name="Create").click()
    page.get_by_label("Submit expense").get_by_text("Submit expense").click()
    page.get_by_label("Manual").click()
    page.get_by_placeholder("0").fill("333")
    page.locator("#numPadContainerView").get_by_role("button", name="Next").click()
    page.get_by_test_id("selection-list").get_by_text("Merchant").click()
    page.get_by_role("textbox", name="Merchant").fill("merchant3")
    page.get_by_role("button", name="Save").click()
    page.get_by_role("button", name="Submit").click()

    # View expense report
    page.get_by_role("button", name="View details").click()

    page.get_by_label("Cash").nth(2).click(button="right")
    page.get_by_label("Hold").click()
    page.get_by_role("textbox", name="Reason").fill("Reason1")
    page.get_by_role('button', name="Hold expense").click()

    page.get_by_label("Cash").nth(1).click(button="right")
    page.get_by_label("Hold").click()
    page.get_by_role("textbox", name="Reason").fill("Reason2")
    page.get_by_role('button', name="Hold expense").click()

    # Go offline
    settings.click()
    page.locator('div[aria-label="Troubleshoot"]').click()
    page.locator('button[aria-label="Force offline"]').click()
    page.get_by_label("Inbox").click()
    workspace.click()

    page.get_by_role("button", name="View details").get_by_role("button").click()
    page.keyboard.press('Enter')
    page.get_by_role("button", name="View details").get_by_text(f'{workspace_name} owes').click()

    page.get_by_label("Cash").get_by_text('Hold').nth(1).click()
    page.mouse.click(0,0)
    page.get_by_role('button', name='for merchant1').first.click()

    # Final assertion
    expect(page.get_by_role('button', name='Unhold')).to_be_visible(timeout=10)


