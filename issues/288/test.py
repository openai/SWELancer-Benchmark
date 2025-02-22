import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import pytest
from playwright.sync_api import TimeoutError, sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page

EXPENSIFY_URL = "https://dev.new.expensify.com:8082/"


def login_user(page, email, first_name="John", last_name="Doe"):
    """
    Log into the Expensify app.
    """

    page.goto(EXPENSIFY_URL)

    page.get_by_test_id("username").fill(email)
    page.get_by_role("button", name="Continue").click()

    try:
        expect(page.get_by_test_id("SignInPage").get_by_test_id("validateCode")).to_be_visible(timeout=7000)
    except (AssertionError, TimeoutError):

        page.get_by_test_id("SignInPage").get_by_role("button", name="Join").click()
    
    try:
        expect(page.get_by_text("What do you want to do today?")).to_be_visible(timeout=10000)
    except (AssertionError, TimeoutError):
        pass
    else:

        page.get_by_label("Track and budget expenses").click()
        page.get_by_role("textbox", name="First name").fill(first_name)
        page.get_by_role("textbox", name="Last name").fill(last_name)
        page.get_by_role("button", name="Continue").click()

        try:
            page.get_by_role("button", name="Back").first.click(timeout=3000)
        except (AssertionError, TimeoutError):
            pass

    try:
        page.get_by_role("button", name="Close").click(timeout=3000)
    except (AssertionError, TimeoutError):
        pass

    expect(page.get_by_test_id("BaseSidebarScreen")).to_be_visible(timeout=10000)


def create_team(page: Page, first_name: str, last_name: str):
    page.locator('input[name="fwork"]').fill("Turingg")
    page.get_by_role("button", name="Continue").last.click()
    page.wait_for_timeout(1000)

    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()
    page.wait_for_timeout(1000)

def check_offline_delete(page: Page):

    workspace_chat = page.locator('button[aria-label="Navigates to a chat"]').nth(1)
    expect(workspace_chat).to_be_visible()
    workspace_chat.click()
    page.wait_for_timeout(1000)

    composer = page.locator('div[aria-placeholder="Write something..."]').nth(1)
    composer.fill("hello")
    page.wait_for_timeout(1000)

    send_button = page.locator('button[aria-label="Send"]').nth(1)
    expect(send_button).to_be_visible()
    send_button.click()
    page.wait_for_timeout(1000)

    span_element = page.locator('span:has-text("hello")')
    span_element.click(button="right")
    page.wait_for_timeout(1000)

    reply_in_thread = page.locator('div[aria-label="Reply in thread"]')
    expect(reply_in_thread).to_be_visible()
    reply_in_thread.click()
    page.wait_for_timeout(1000)

    composer = page.locator('div[aria-placeholder="Write something..."]').nth(2)
    composer.fill("reply")
    page.wait_for_timeout(1000)

    send_button = page.locator('button[aria-label="Send"]').nth(2)
    expect(send_button).to_be_visible()
    send_button.click()
    page.wait_for_timeout(1000)

    workspace_chat = page.locator('button[aria-label="Navigates to a chat"]').nth(1)
    expect(workspace_chat).to_be_visible()
    workspace_chat.click()
    page.wait_for_timeout(1000)

    composer = page.locator('div[aria-placeholder="Write something..."]').nth(2)
    composer.fill("reply2")
    page.wait_for_timeout(1000)

    send_button = page.locator('button[aria-label="Send"]').nth(2)
    expect(send_button).to_be_visible()
    send_button.click()
    page.wait_for_timeout(1000)

    my_settings = page.locator('button[aria-label="My settings"]')
    expect(my_settings).to_be_visible()
    my_settings.click()
    page.wait_for_timeout(1000)

    trouble = page.locator('div[aria-label="Troubleshoot"]')
    expect(trouble).to_be_visible()
    trouble.click()
    page.wait_for_timeout(1000)

    button_off = page.locator('button[aria-label="Force offline"]').click()
    page.wait_for_timeout(1000)

    inbox = page.locator('button[aria-label="Inbox"]').click()
    page.wait_for_timeout(1000)

    workspace_chat = page.locator('button[aria-label="Navigates to a chat"]').nth(1)
    expect(workspace_chat).to_be_visible()
    workspace_chat.click()
    page.wait_for_timeout(1000)

    span_element = page.locator('span:has-text("hello")')
    span_element.click(button="right")
    page.wait_for_timeout(1000)

    reply_in_thread = page.locator('div[aria-label="Delete comment"]')
    expect(reply_in_thread).to_be_visible()
    reply_in_thread.click()
    page.wait_for_timeout(1000)

    delete = page.locator('button:has-text("Delete")')
    expect(delete).to_be_visible()
    delete.click()
    page.wait_for_timeout(1000)

    span_element = page.locator('span:has-text("reply2")')
    span_element.click(button="right")
    page.wait_for_timeout(1000)

    reply_in_thread = page.locator('div[aria-label="Delete comment"]')
    expect(reply_in_thread).to_be_visible()
    reply_in_thread.click()
    page.wait_for_timeout(1000)

    delete = page.locator('button:has-text("Delete")').nth(1)
    expect(delete).to_be_visible()
    delete.click()
    page.wait_for_timeout(1000)

    locator = page.locator('div:nth-child(4) > div:nth-child(2) > div:nth-child(2) > div > div > div > div > div > div > div > div > div:nth-child(3) > div > div:nth-child(2) > div > div > div:nth-child(3) > div > div > div > div:nth-child(2) > div > div > div')
    locator.click(timeout=1000) 
    deleted_message_button = page.locator('button[aria-label="[Deleted message]"]')

    assert deleted_message_button.is_visible(), "The deleted message button should be visible"


@pytest.mark.parametrize("first_name, last_name", [("Rcocky", "Sai")])
def test_run(first_name: str, last_name: str) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=["--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"])

        page = browser.new_page()
        user_email = 'ibukunsamuel999+1733043350@gmail.com'
        login_user(page, user_email, first_name=first_name, last_name=last_name)
        check_offline_delete(page)

        browser.close()

if __name__ == "__main__":
    pytest.main([__file__])
