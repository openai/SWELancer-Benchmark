import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright._impl._page import Page
from playwright.sync_api import sync_playwright, expect

first_name = "Milan"
last_name = "T"

# Utility to generate a random email
def generate_random_email():
    timestamp = "661151210"
    return f"freelanceapptest+{timestamp}@gmail.com"

def login_user(page: Page) -> None:
    # Step 1: Enter email and click continue
    username_input = page.get_by_test_id("username")
    username_input.click()

    username_input.fill(generate_random_email())

    continue_button = page.get_by_role("button", name="Continue")
    continue_button.click()
    
    # Step 2: Click join button
    join_button = page.get_by_role("button", name="Join")
    join_button.click()
    
     # Step 3: Select 'Track and budget expenses' in onboarding page and click Continue
    track_expenses_text = page.get_by_text("Track and budget expenses")
    track_expenses_text.click()

def enter_user_information(page:Page) -> None:
    # Step 1: Enter first name, last name and click continue
    first_name_input = page.get_by_role("textbox", name="First name")
    first_name_input.fill(first_name)

    first_name_input.press("Tab")

    last_name_input = page.get_by_role("textbox", name="Last name")
    last_name_input.fill(last_name)
    
    # Step 2: Click continue button
    continue_button_after_names = page.get_by_role("button", name="Continue")
    continue_button_after_names.click()

def reproduce_scenario(page: Page) -> None:
    # Step 1 : Create workspace
    page.get_by_label("My settings").click()
    page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").get_by_text("Workspaces").click()
    page.get_by_label("New workspace").nth(1).click()
    page.get_by_label("Back").click()
    page.get_by_label("Inbox").click()
    page.get_by_label("Start chat (Floating action)").click()
    page.get_by_text("Start chat").click()
    
    # Step 2 : Create room
    page.get_by_label("Room", exact=True).click()
    page.get_by_placeholder("social").click()

    # Step 3 : Fill the room name with division sign (÷)
    page.get_by_placeholder("social").fill("myroom÷")
    
    # Step 4 : Unfocused the room name input
    page.get_by_label("Room description (optional)").locator("div").nth(3).click()

    # Verify error message pop up
    invalid_text_message = page.locator("text=Room names can only include lowercase letters, numbers, and hyphens.")
    expect(invalid_text_message).to_be_visible()

def test_roomname_with_division_sign() -> None: 
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
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
        page.goto("https://dev.new.expensify.com:8082/")
        
        # Step 1: Login user 
        login_user(page)

        # Step 2: Enter User Information
        enter_user_information(page)
        page.wait_for_timeout(2000)
        
        # Step 3: Reproduce scenario
        reproduce_scenario(page)
        page.wait_for_timeout(2000)

        context.close()
        browser.close()