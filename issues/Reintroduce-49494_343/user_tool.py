import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright._impl._page import Page
from playwright.sync_api import sync_playwright
from utils.trace_cleaner import trace_cleaner

first_name = "Alice"
last_name = "Aliceoglu"
workspace_name = f"{first_name} {last_name}'s Workspace"


def login_user(page: Page) -> None:
    # Step 1: Enter email and click continue
    username_input = page.get_by_test_id("username")
    username_input.click()

    username_input.fill("aliceoglualice+881351517@gmail.com")

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
    # Step 1: Create workspace
    start_chat_button = page.get_by_label("Start chat (Floating action)")
    start_chat_button.click()

    new_ws_button = page.get_by_text("New workspace")
    new_ws_button.click()
    
    back_button = page.get_by_label("Back")
    back_button.click()

    inbox_button = page.get_by_label("Inbox")
    inbox_button.click()
    page.wait_for_timeout(1000)
    
    # Step 1: Start a chat room
    start_button = page.get_by_label("Start chat (Floating action)")
    start_button.click()

    start_chat_button = page.get_by_text("Start chat")
    start_chat_button.click()

    room_button = page.get_by_label("Room", exact=True)
    room_button.click()
    
    # Step 1: Create a room with name of ccc
    page.get_by_placeholder("social").fill("ccc")
    
    chat_ws_selection_button = page.get_by_test_id("WorkspaceNewRoomPage").get_by_text("Workspace", exact=True).first
    chat_ws_selection_button.click()

    ws_text = page.get_by_test_id("ValueSelectorModal").get_by_label(workspace_name)
    ws_text.click()

    create_room_button = page.get_by_role("button", name="Create room")
    create_room_button.click()
    page.wait_for_timeout(1000)
    
    # Step 1: Send #admins and #ccc as message
    page.locator("#composer").last.fill("#admins")
    page.get_by_text("admins", exact=True).click()
    page.locator("#composer").last.fill("#admins #ccc")
    page.get_by_text("ccc", exact=True).click()
    
    send_button = page.locator("button[aria-label='Send']").last
    send_button.click()
    
    # Step 1: Go to chats section to control room name
    search_button = page.locator("button[aria-label='Search']").first
    search_button.click()

    chat_button = page.get_by_text("Chats")
    chat_button.click()

    # Verify the room name has background color
    element = page.locator("span:has-text('#ccc')").first
    background_color = element.evaluate("element => window.getComputedStyle(element).backgroundColor")
    assert background_color != "rgba(0, 0, 0, 0)", "Element has no background color."


def test_room_name_is_highlighted() -> None:
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
            slow_mo=1000
        )
        context = browser.new_context(ignore_https_errors=True)

        # Start tracing
        context.tracing.start(
            title="test_room_name_is_highlighted",
            screenshots=True,
            snapshots=True
        )

        page = context.new_page()
        page.goto("https://dev.new.expensify.com:8082/")
        
        try:
            # Step 1: Login user 
            login_user(page)
            page.wait_for_timeout(1000)

            # Step 2: Enter User Information
            enter_user_information(page)
            page.wait_for_timeout(1000)
            
            # Step 3: Reproduce scenario
            reproduce_scenario(page)
            page.wait_for_timeout(1000)
        except Exception as e:
            # We still want to raise the exception after saving the trace
            raise e
        finally:
            # Stop tracing and save
            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            context.close()
            browser.close()
