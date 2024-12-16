import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright

TEMP = 49494

def perform_first_time_user_setup(page):
    username_input = page.get_by_test_id("username")
    username_input.click()

    username_input.fill(f"ikhanle001+{TEMP}@gmail.com")

    continue_button = page.get_by_role("button", name="Continue")
    continue_button.click()
    
    join_button = page.get_by_role("button", name="Join")
    join_button.click()
    
    track_expenses_text = page.get_by_text("Track and budget expenses")
    track_expenses_text.click()

    first_name_input = page.get_by_role("textbox", name="First name")
    first_name_input.fill('first_name')

    first_name_input.press("Tab")

    last_name_input = page.get_by_role("textbox", name="Last name")
    last_name_input.fill('last_name')
    
    continue_button_after_names = page.get_by_role("button", name="Continue")
    continue_button_after_names.click()

def create_workspace(page):
    workspace_name = f"WS-{TEMP}"
    page.get_by_label("My settings").click()
    page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()
    page.get_by_role("button", name="New workspace").first.click()
    page.wait_for_timeout(2000)
    page.get_by_test_id("WorkspacePageWithSections").get_by_text("Name").first.click()
    page.get_by_role("textbox", name="Name").press("ControlOrMeta+a")
    page.get_by_role("textbox", name="Name").fill(workspace_name)
    page.get_by_role("button", name="Save").click()
    page.wait_for_timeout(2000)
    page.get_by_label("Back").click()
    page.get_by_label("Inbox").click()

def validate_room_tags_highlighted(page):
    inbox_button = page.get_by_label("Inbox")
    inbox_button.click()
    page.wait_for_timeout(1000)

    start_button = page.get_by_label("Start chat (Floating action)")
    start_button.click()

    start_chat_button = page.get_by_text("Start chat")
    start_chat_button.click()

    room_button = page.get_by_label("Room", exact=True)
    room_button.click()
    
    page.get_by_placeholder("social").fill("target")
    
    chat_ws_selection_button = page.get_by_test_id("WorkspaceNewRoomPage").get_by_text("Workspace", exact=True).first
    chat_ws_selection_button.click()

    ws_text = page.get_by_test_id("ValueSelectorModal").get_by_label(f"WS-{TEMP}")
    ws_text.click()

    create_room_button = page.get_by_role("button", name="Create room")
    create_room_button.click()
    page.wait_for_timeout(1000)
    
    page.locator("#composer").last.fill("#admins")
    page.get_by_text("admins", exact=True).click()
    page.locator("#composer").last.fill("#admins #target")
    page.get_by_text("target", exact=True).click()
    
    send_button = page.locator("button[aria-label='Send']").last
    send_button.click()
    
    search_button = page.locator("button[aria-label='Search']").first
    search_button.click()

    chat_button = page.get_by_text("Chats")
    chat_button.click()

    element = page.locator("span:has-text('#target')").first
    background_color = element.evaluate("element => window.getComputedStyle(element).backgroundColor")
    assert background_color != "rgba(0, 0, 0, 0)", "Element has no background color."

def test_room_tags_highlighted_in_search():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, slow_mo=1000, args=[
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
        ])
        context = browser.new_context()
        page = context.new_page()

        page.goto("https://dev.new.expensify.com:8082/")

        perform_first_time_user_setup(page)
        create_workspace(page)
        validate_room_tags_highlighted(page)

        context.close()
        browser.close()
