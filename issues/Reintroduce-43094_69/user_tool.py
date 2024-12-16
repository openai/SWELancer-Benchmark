import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright
from playwright._impl._page import Page
import logging
from utils.trace_cleaner import trace_cleaner  # <--- ADDED

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Sign In to Expensify
def sign_in_new_dot(page: Page, email: str):
    """
    Sign in into the new Expensify dot.
    """
    # Go to URL
    page.goto("https://dev.new.expensify.com:8082/")

    # Enter email
    page.get_by_test_id("username").fill(email)
    page.get_by_role("button", name="Continue").click()

    # Await OTP
    otp = "123456"
    page.get_by_test_id("validateCode").fill(otp)

    # Wait sign in to complete
    page.get_by_text("Please enter the magic code").wait_for(state="hidden")
    logging.info("Sign in complete.")

    return page



def create_new_workspace(
    page: Page,
) -> Page:
    # Step 1: Click on + icon and click on "New workspace"
    plus_icon = page.locator('button[aria-label="Start chat (Floating action)"]')
    plus_icon.wait_for()
    plus_icon.click()

    new_workspace_button = page.locator('div[aria-label="New workspace"]')
    new_workspace_button.wait_for()
    new_workspace_button.click()

    # Step 2: Click on Back arrow to go back 
    back_arrow_button = page.locator('button[aria-label="Back"]')
    back_arrow_button.wait_for()
    back_arrow_button.click()

    return page


def create_room_in_workspace(
    page: Page,
    room_name: str
) -> Page:
    # Step 1: Click on + icon and click start chat
    plus_icon = page.locator('button[aria-label="Start chat (Floating action)"]')
    plus_icon.wait_for()
    plus_icon.click()

    start_chat = page.locator('div[aria-label="Start chat"]')
    start_chat.wait_for()
    start_chat.click()

    # Step 2: Click on # Room
    room_button = page.locator('button[aria-label="Room"]')
    room_button.wait_for()
    room_button.click()

    page.locator('input[aria-label="Room name"]').fill(room_name)

    page.locator('button[tabindex="0"][data-listener="Enter"]', has_text="Create room").click()

    return page


def login_user(page: Page, user_email: str, first_name="Milan", last_name="T") -> Page:

    # Step 1: Open expensify url
    page.goto('https://dev.new.expensify.com:8082/')

    # Step 2: Enter email and click continue
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(1000)

    # Step 3: Click join button
    try:
        page.locator('button[tabindex="0"]').click()
    except Exception:
        pass
    page.locator("text=What do you want to do today?").wait_for()

    # Step 4: Select 'Track and budget expenses' in onobarding page and click Continue
    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()

    # Step 5: Enter first name, last name and click continue
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()

    return page


def add_member_to_workspace(
    page: Page,
    member_email: str = "milan.thummar-1729422465@gmail.com"
) -> Page:
    # Step 1: Click settings
    my_settings = page.locator('button[aria-label="My settings"]')
    my_settings.wait_for()
    my_settings.click()

    # Step 2: Click on workspaces button
    workspaces = page.locator('div[aria-label="Workspaces"][role="menuitem"]')
    workspaces.wait_for()
    workspaces.click()

    # Step 3: Click on first workspace
    button = page.get_by_role("button", name="row")
    button.click()

    # Step 4: Click on members button
    members_button = page.locator('div[aria-label="Members"][role="menuitem"]')
    members_button.wait_for()
    members_button.click()

    # Step 5: Click on invite members button
    invite_members = page.get_by_text("Invite member")
    invite_members.wait_for()
    invite_members.click()

    # Step 6: Enter email and click continue
    page.locator('input[type="text"]').fill(member_email)
    page.wait_for_timeout(1000)
    try:
        button = page.locator('button[aria-label="Bob T"]').nth(1)
        button.click()
    except:
        button = page.locator(f'button[aria-label="{member_email}"]').nth(1)
        button.click()

    page.locator('button[tabindex="0"][data-listener="Enter"]').nth(0).click()
    page.locator('button[tabindex="0"][data-listener="Enter"]', has_text="Invite").click()
    page.wait_for_timeout(1000)

    # Click on Back arrow to go back
    back_arrow_button = page.locator('button[aria-label="Back"]')
    back_arrow_button.click()

    return page


def test_duplicated_search():
    with sync_playwright() as p:
        # --------------------------------------------------
        # First browser session (Step 1 & 2: Bob logs in, then close browser)
        # --------------------------------------------------
        browser1 = p.chromium.launch(headless=True, slow_mo=1000,
                                     args=[
                                       '--disable-web-security',
                                       '--disable-features=IsolateOrigins,site-per-process',
                                       '--ignore-certificate-errors'
                                     ])
        context1 = browser1.new_context()
        trace1_path = "/app/expensify/user_tool/output_browser1.zip"
        context1.tracing.start(screenshots=True, snapshots=True, sources=True)
        page1 = context1.new_page()

        bob_email = "bobexpensifytest+1734083386@gmail.com"
        try:
            # Step 1: Login as Bob
            page1 = login_user(page1, bob_email, first_name='Bob')
            page1.wait_for_timeout(2000)
            # Step 2: We'll close this browser after we finish this block
        except Exception as e:
            logging.exception(e)
        finally:
            context1.tracing.stop()
            context1.tracing.export(path=trace1_path)
            trace_cleaner(trace1_path)
            browser1.close()

        # --------------------------------------------------
        # Second browser session (Steps 3 to 7: Alice logs in, create workspace, add Bob, create rooms, close)
        # --------------------------------------------------
        browser2 = p.chromium.launch(headless=True, slow_mo=1000,
                                     args=[
                                       '--disable-web-security',
                                       '--disable-features=IsolateOrigins,site-per-process',
                                       '--ignore-certificate-errors'
                                     ])
        context2 = browser2.new_context()
        trace2_path = "/app/expensify/user_tool/output_browser2.zip"
        context2.tracing.start(screenshots=True, snapshots=True, sources=True)
        page2 = context2.new_page()

        alice_email = "bobexpensifytest+1734083385@gmail.com"
        try:
            # Step 3: Login as Alice
            page2 = login_user(page2, alice_email, first_name='Alice')

            # Step 4: Create Workspace as Alice
            page2 = create_new_workspace(page2)

            # Step 5: Add Bob to workspace
            page2 = add_member_to_workspace(page2, bob_email)

            # Step 6: Create two rooms
            page2 = create_room_in_workspace(page2, "room1")
            page2 = create_room_in_workspace(page2, "room2")
            page2.wait_for_timeout(2000)
            # Step 7: We'll close and open a new browser after we finish this block
        except Exception as e:
            logging.exception(e)
        finally:
            context2.tracing.stop()
            context2.tracing.export(path=trace2_path)
            trace_cleaner(trace2_path)
            browser2.close()

        # --------------------------------------------------
        # Third browser session (Steps 8 & 9: Bob logs back in, search for room1, check duplication)
        # --------------------------------------------------
        browser3 = p.chromium.launch(headless=True, slow_mo=1000,
                                     args=[
                                       '--disable-web-security',
                                       '--disable-features=IsolateOrigins,site-per-process',
                                       '--ignore-certificate-errors'
                                     ])
        context3 = browser3.new_context()
        trace3_path = "/app/expensify/user_tool/output_browser3.zip"
        context3.tracing.start(screenshots=True, snapshots=True, sources=True)
        page3 = context3.new_page()

        try:
            # Step 8: Log in as Bob again
            page3 = sign_in_new_dot(page3, bob_email)

            # Step 9: Click on find button and confirm #room1 is found exactly once
            find_button = page3.locator('div[aria-label="Find something..."]')
            find_button.wait_for()
            find_button.click()

            page3.locator('input[aria-label="Name, email, or phone number"]').fill("room1")

            button_locator = page3.locator('button[aria-label="#room1"][role="button"]')
            button_locator.first.wait_for(state="visible")
            assert button_locator.count() == 1, "Expected exactly 1 #room1 in the search results"
        except Exception as e:
            logging.exception(e)
        finally:
            context3.tracing.stop()
            context3.tracing.export(path=trace3_path)
            trace_cleaner(trace3_path)
            browser3.close()