import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import random
import string
import time

import pytest
from playwright.sync_api import sync_playwright, expect
from playwright._impl._browser import Browser
from playwright._impl._page import Page


def generate_random_email():
    return "testerbro7077+956723@gmail.com"

@pytest.fixture
def setup_playwright():

    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(channel="chrome", headless=True, args=[
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
            "--ignore-certificate-errors"
    ])
    page = browser.new_page()
    yield page  # Yield the page object to the test function
    browser.close()
    playwright.stop()


def login_user(page: Page, user_email: str, first_name: str, last_name: str) -> tuple[Browser, Page, str]:

    page.goto(f'https://dev.new.expensify.com:8082')


    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()
    time.sleep(2)


    try:
        page.wait_for_timeout(2000)
        page.locator('button[tabindex="0"]').click()
        page.wait_for_timeout(1000)
    except Exception:
        pass
    expect(page.locator("text=What do you want to do today?")).to_be_visible()


    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()
    time.sleep(1)


    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()
    time.sleep(1)


def task_description_multiline_issue(page: Page, first_name: str, last_name: str) -> bool:

    user_email = generate_random_email()


    login_user(page, user_email, first_name, last_name)
    welcome_dialog = page.locator('button:has(div:text("Get Started"))') # Incase the welcome dialog shows up
    if welcome_dialog.is_visible(timeout=3000):
        welcome_dialog.click()


    personal_space = page.locator('button[aria-label="Navigates to a chat"]').last
    expect(personal_space).to_be_visible()
    personal_space.click()
    page.wait_for_timeout(1000)
    page.locator('button[aria-label="Create"]').last.click()
    page.wait_for_timeout(1000)
    page.get_by_text("Assign task").click()
    page.wait_for_timeout(1000)

    page.locator('input[aria-label="Title"]').fill("Test the Chat")
    page.wait_for_timeout(1000)

    description_field = page.locator('div[aria-label="Description (optional)"][contenteditable="true"]').first
    description_field.fill(''.join(random.choices(string.printable, k=100)))
    page.wait_for_timeout(1000)


    return description_field.get_attribute('aria-multiline') == "true" and description_field.evaluate(
        'el => el.classList.contains("react-native-live-markdown-input-multiline")'
    )

@pytest.mark.parametrize("first_name, last_name", [("Test", "User")])
def test_task_description_multiline_issue(setup_playwright, first_name, last_name):
    page = setup_playwright
    issue_not_found = task_description_multiline_issue(page, first_name, last_name)
    assert (
        issue_not_found
    ), "Allow adding newlines in description for tasks not implemented"