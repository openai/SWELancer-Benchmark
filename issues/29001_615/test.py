import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
from playwright.sync_api import sync_playwright, expect
from playwright._impl._page import Page 
import os

def launch_browser(platform='desktop', browser_type='chromium'):
    """
    Launch a persistent browser with the specified platform
    """

    playwright = sync_playwright().start()
    data_dir = f'{browser_type}_{platform}_context'
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    mobile_context = {}

    if platform.lower() == 'mobile':
        mobile_context = {
            'viewport': {'width': 540, 'height': 864},
            'is_mobile': True,
        }

    context = playwright[browser_type].launch_persistent_context(
        data_dir,
        headless=True,
        **mobile_context, args=["--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"], 
        proxy={"server": "http://localhost:8080"}, slow_mo=500)
    
    # persistent context already has the page
    page = context.pages[0]
    
    return playwright, context, page


def login_user_if_not_logged_in(
        page: Page, 
        first_name="Asaad", 
        last_name="I", 
        email: str = "testuser+29001@gmail.com", 
        platform="desktop",
    ):
    # Launch chromiun and open ne   w page

    # Step 1: Open expensify url
    page.goto('https://dev.new.expensify.com:8082/')

    page.wait_for_load_state('load')

    try:
        # If the user is not logged in, the email input should be visible
        expect(page.locator('input[type="email"]')).to_be_visible(timeout=3000)
    except:
        # If the user is already logged in, do nothing
        return

    # Step 3: Enter email and click continue
    page.locator('input[type="email"]').fill(email)
    page.locator('button', has_text="Continue").click()

    # Step 4: Click join button
    page.locator('button', has_text="Join").click()

    # Step 5: Select 'Track and budget expenses' in onobarding page and click Continue
    # wait for the text to be visible
    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()

    # Step 6: Enter first name, last name and click continue
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("form").get_by_role("button", name="Continue").click()

    # Step 7: Wait for the onboarding process to complete, 
    # this can be crucial to avoid any flakiness in the test
    # For Narrow layout, open the chat for Track an expense
    if platform.lower() == 'mobile':
        page.get_by_label('Last chat message preview').filter(has_text='task for Track an expense').click()
    # For Narrow layout, click on Back button to navigate to inbox
    if platform.lower() == 'mobile':
        page.get_by_label("Back").click()


def verify_start_chat_focus(page: Page):
    """
    Verify that the start chat page is focused when navigating back and forth between start chat and start room pages
    """
    # Step 1: Navigate to Workspaces settings page
    page.get_by_label("My settings").click()
    page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()

    # create a new workspace if not already created
    if page.get_by_label("row").count() == 0:
        page.get_by_label("New workspace").first.click()
        page.get_by_label("Back").click()
    
    # Step 2: Navigate to inbox
    page.get_by_label("Inbox").click()

    # Step 3: Open + button to click on start chat
    page.get_by_label("Start chat (Floating action)").click()
    page.get_by_label("Start chat", exact=True).click()

    # Step 4: Navigate back and forth between start chat and start room pages
    for _ in range(3):
        page.get_by_label("Room", exact=True).click()
        page.get_by_test_id("NewChatSelectorPage").get_by_label("Chat").click()
        
    # Step 5: Verify that the start chat page is focused
    expect(page.get_by_test_id("selection-list-text-input")).to_be_focused()


def test_start_chat_focus():
    """
    Test that the start chat page is focused
    When navigating back and forth between start chat and start room pages
    """

    # Step 1: Launch the browser
    platform = "desktop"
    browser_type = 'chromium'
    playwright, context, page = launch_browser(platform, browser_type)

    # Step 2: Generate an email
    email = "expensify66+29001@gmail.com"

    # Step 3: Login to expensify
    login_user_if_not_logged_in(page, "Asaad", "I", email, platform)

    # Step 4: Verify that the chat is focused
    verify_start_chat_focus(page)

    # Step 5: Close the browser
    context.close()
    playwright.stop()   

