import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from playwright._impl._page import Page

SITE_URL = "https://dev.new.expensify.com:8082/"
PRIMARY_EMAIL = "expensifyolddot+1733831382@gmail.com"
FIRST_NAME = "Expenolddot"
LAST_NAME = "1733831382"

def login_user(
        page: Page, 
        first_name="Asaad", 
        last_name="I", 
        email: str = "testuser@gmail.com", 
        platform="chromium"
    ):
    # Launch chromiun and open new page

    # Step 1: Open expensify url
    page.goto(SITE_URL)

    # Step 2: Enter email and click continue
    page.locator('input[type="email"]').fill(email)
    page.locator('button', has_text="Continue").click()

    # Step 3: Click join button
    page.locator('button', has_text="Join").click()

    # Step 4: Select 'Track and budget expenses' in onobarding page and click Continue
    # wait for the text to be visible
    page.wait_for_timeout(2000)
    if page.locator("text='Track and budget expenses'").is_visible():
        page.locator("text='Track and budget expenses'").click()
        page.get_by_role("button", name="Continue").click()

        # Step 5: Enter first name, last name and click continue
        page.locator('input[name="fname"]').fill(first_name)
        page.locator('input[name="lname"]').fill(last_name)
        page.get_by_role("form").get_by_role("button", name="Continue").click()

    # Step 7: Wait for the onboarding process to complete, 
    # this can be crucial to avoid any flakiness in the test
    # For Narrow layout, open the chat for Track an expense
    page.reload() # Need to reload for replaying the test
    if platform.lower() in ['ios', 'android']:
        page.get_by_label('Last chat message preview').filter(has_text='task for Track an expense').wait_for()
        page.get_by_label('Last chat message preview').filter(has_text='task for Track an expense').first.click()
    page.get_by_label("guided-setup-track-personal-").wait_for()
    # For Narrow layout, click on Back button to navigate to inbox
    if platform.lower() in ['ios', 'android']:
        page.get_by_label("Back").click()
        page.get_by_label("Inbox").wait_for()

def verify_go_back_works_after_reload_on_flag_page(page: Page):
    # step 1: Go to a public page
    page.goto('https://dev.new.expensify.com:8082/r/5624984165978443')
    page.wait_for_timeout(5000)

     # Step 2: Click on the message and click on Flag as offensive
    page.get_by_label("Chat message", exact=True).first.click(button="right")
    page.get_by_label("Flag as offensive").click()

    # Step 3: Wait for the Choose a reason for flagging text to be visible
    page.get_by_text("Choose a reason for flagging").wait_for()

    # Step 4: Go Back, it should be inside the page.
    page.get_by_test_id("FlagCommentPage").get_by_label("Back").click()
    expect(page.get_by_label("Chat message", exact=True).first).to_be_visible()

    # Step 5: Click on the message again and click on Flag as offensive
    page.get_by_label("Chat message", exact=True).first.click(button="right")

    page.get_by_label("Flag as offensive").click()

    # Step 6: Again wait for the Choose a reason for flagging text to be visible
    page.get_by_text("Choose a reason for flagging").wait_for()
    
    # Step 7: This time reload the page
    page.reload()

    # Step 8: Go Back and verify that it should be inside the the chat page.
    page.get_by_test_id("FlagCommentPage").get_by_label("Back").click()
    expect(page.get_by_label("Chat message", exact=True).first).to_be_visible()


def test_go_back_after_reload_on_flag_page():
    """
    Test to verify that the go back works after reload on flag page
    """
    with sync_playwright() as p:
        platform = "ios"

        # Step 1: Launch the browser
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--ignore-certificate-errors",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process"
            ],
            proxy={"server": "http://localhost:8080"},
            slow_mo=500
        )

        device_config = p.devices['iPhone 14']
        context_args = { "timezone_id": "Asia/Kathmandu" }
        merged_context_args = {**device_config, **context_args}
        context = browser.new_context(**merged_context_args)
        page = context.new_page()

        # Step 2: Login to expensify
        login_user(page, FIRST_NAME, LAST_NAME, PRIMARY_EMAIL, platform)

        # Step 3: Verify that go back works after reload on flag page
        verify_go_back_works_after_reload_on_flag_page(page)

        # Step 4: Close browser
        context.close()
        browser.close()