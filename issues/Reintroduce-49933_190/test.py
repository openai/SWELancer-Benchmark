import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
import pytest
import random
from playwright.sync_api import sync_playwright, Page

# Gmail credentials for generating user info
GMAIL_NAME = "rgulraiz2000"
GMAIL_APP_PASSWORD = "kepw uquj myoa npvj"

# Utility to generate user info
def get_test_user_info(seed=None, first_name=None, last_name=None):
    if first_name is None:
        first_name = GMAIL_NAME
    if last_name is None:
        last_name = ""
    email = f"{GMAIL_NAME}+{seed}@gmail.com" if seed is not None else f"{GMAIL_NAME}@gmail.com"
    return {"email": email, "password": GMAIL_APP_PASSWORD, "first_name": first_name, "last_name": last_name}

@pytest.fixture
def setup_playwright():
    # Initialize Playwright
    playwright = sync_playwright().start()
    # Launch browser for user 1
    browser = playwright.chromium.launch(channel="chrome", headless=True, slow_mo=2000, args=[
        "--disable-web-security",
        "--disable-features=IsolateOrigins,site-per-process",
    ])
    page = browser.new_page()
    yield page
    # Cleanup
    browser.close()
    playwright.stop()

# Function to log in to the application
def login_user(page: Page, email: str, first_name: str, last_name: str):
    page.goto("https://dev.new.expensify.com:8082/")
    page.locator('input[type="email"]').fill(email)
    page.locator('button[tabindex="0"]').click()
    time.sleep(1)
    # Join process and continue onboarding steps
    try:
        page.locator('button[tabindex="0"]').click()
        time.sleep(1)
    except Exception:
        pass
    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()
    time.sleep(1)
    # Enter user details and complete onboarding
    try:
        page.locator('input[name="fname"]').fill(first_name)
        page.locator('input[name="lname"]').fill(last_name)
        page.get_by_role("button", name="Continue").last.click()
    except Exception:
        pass

# Function to create a group chat
def create_group_chat(page: Page, users):
    div_get_started_here = page.locator('div:has-text("Get started here!")')
    if div_get_started_here.count() > 0:
        page.locator('button[aria-label="Close"]').last.click()

    for user in users:
        input_field = page.locator('input[data-testid="selection-list-text-input"]')
        input_field.fill(user)
        time.sleep(1)
        page.locator('button:has(div:text("Add to group"))').nth(1).click()
        time.sleep(1)

    input_field.press("Enter")
    time.sleep(1)
    page.locator('div[data-testid="selection-list"]').nth(1).press("Enter")
    time.sleep(1)

# Function to delete a user from the group
def delete_user_from_group(page: Page):
    details = page.locator('button[aria-label="Details"]').last
    details.click()
    all_members = page.locator('div[aria-label="Members"]')
    all_members.click()

    selection_list = page.locator('div[data-testid="selection-list"]')
    delete_last_user = selection_list.locator('div[dir="auto"]', has_text="billgates+98@gmail.com").last
    delete_last_user.click()

    remove_from_group = page.locator('button[role="button"]', has_text='Remove from group')
    remove_from_group.click()

    confirm_delete = page.locator('button[data-listener="Enter"]', has_text='Remove')
    confirm_delete.click()

    back_btn_1 = page.locator('button[aria-label="Back"]').last
    back_btn_1.click()
    back_btn_2 = page.locator('button[aria-label="Back"]').last
    back_btn_2.click()

@pytest.mark.usefixtures("setup_playwright")
def test_welcome_group_message(setup_playwright):
    page = setup_playwright

    # Generate static user details
    timestamp = int(time.time())
    user_info = get_test_user_info(seed=timestamp, first_name="John", last_name="Doe")

    # Additional users to add to the group
    users = [
        "donaldtrump+98@gmail.com",
        "elonmusk+98@gmail.com",
        "billgates+98@gmail.com",
    ]

    # Step 1: Login user
    login_user(page, user_info["email"], user_info["first_name"], user_info["last_name"])

    # Step 2: Navigate to LHN
    # back_btn = page.locator('button[aria-label="Back"]')
    # back_btn.click()

    # Step 3: Click on + icon and click on "Start chat"
    plus_icon = page.locator('button[aria-label="Start chat (Floating action)"]')
    plus_icon.focus()
    plus_icon.click()
    page.wait_for_timeout(2000)

    start_chat = page.locator('div[aria-label="Start chat"]')
    start_chat.click()
    page.wait_for_timeout(2000)

    # Step 4: Create group chat with 3 users
    create_group_chat(page, users)

    # Step 5: Delete one user from the group
    delete_user_from_group(page)

    # Step 6: Check if the deleted user email is displayed in the welcome message
    welcome_msg = page.locator('div[aria-label="Chat welcome message"]')
    is_user_deleted = welcome_msg.get_by_text(str(users[-1])).is_visible()
    page.wait_for_timeout(2000)

    if is_user_deleted:
        assert False, "The removed user is displayed in the welcome group message"
    else:
        assert True, "The removed user is not displayed in the welcome group message"
