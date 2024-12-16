import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect

# Removed PlaywrightContextManager import because we no longer use it directly
# from playwright.sync_api._context_manager import PlaywrightContextManager


def get_user_email():
    return f"nitish.expensify+{103}@gmail.com"


def get_magic_code():
    return "123456"


def login_user(page, first_name="John", last_name="Doe"):
    user_email = get_user_email()
    first_name = 'John'
    last_name = 'Doe'

    # Step 1: Open expensify url
    page.goto('https://dev.new.expensify.com:8082/')

    # Step 2: Enter email and click continue
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()

    try:
        expect(page.get_by_role("button", name="Sign in")).to_be_visible()
        page.get_by_test_id("validateCode").fill(get_magic_code())
    except Exception:
        page.get_by_role("button", name="Join").click()

    try:
        expect(page.locator('div[aria-label="Track and budget expenses"]').nth(0)).to_be_visible()

        # Step 4: Select 'Track and budget expenses' in onboarding page and click Continue
        page.locator('div[aria-label="Track and budget expenses"]').nth(0).click()

        # Step 5: Enter first name, last name and click continue
        page.locator('input[name="fname"]').nth(0).fill(first_name)
        page.locator('input[name="lname"]').nth(0).fill(last_name)
        page.get_by_role("button", name="Continue").nth(0).click()
    except Exception:
        pass

    try:
        get_started_here = page.locator('div', has_text="Get started here!").nth(-1)
        expect(get_started_here).to_be_visible()
        page.get_by_label("Close").nth(-1).click()
    except Exception:
        pass

    return page


def test():
    # We'll import and call trace_cleaner at the end
    from utils.trace_cleaner import trace_cleaner

    with sync_playwright() as p:
        # Launch the browser and create a context
        browser = p.chromium.launch(headless=True, args=[
            "--ignore-certificate-errors",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ], slow_mo=1000)
        context = browser.new_context()

        # Start tracing
        context.tracing.start(screenshots=True, snapshots=True, sources=True)

        # Create a new page
        page = context.new_page()

        try:
            # Step 1: Login user
            login_user(page)

            # Click settings
            click_settings_button = page.locator("[aria-label='My settings']")
            click_settings_button.click()

            # Click workspaces
            click_workspace_button = page.locator("div[aria-label='Workspaces']")
            click_workspace_button.click()

            # Create new workspaces
            create_new_workspace_button = page.locator("[aria-label='New workspace']").nth(0)
            create_new_workspace_button.click()

            # Click Back button
            click_back_button = page.locator("[aria-label='Back']").nth(-1)
            click_back_button.click()

            # Click Inbox
            click_Inbox = page.locator("button[aria-label='Inbox']").nth(-1)
            click_Inbox.click()

            # Click WS chat
            click_WS_chat = page.locator("div", has_text="John Doe's Workspace").nth(-1)
            click_WS_chat.click()

            # Edit input text
            edit_input_text = page.locator('div[contenteditable="true"]').nth(-1)

            # Focus on the div by clicking it
            edit_input_text.fill("hiiii I am here")

            # send the message
            send_message = page.locator("[aria-label='Send']")
            send_message.click()

            # hover the sent message
            hover_message = page.locator('div[aria-label="Chat message"]', has_text="hiiii I am here").nth(-1)
            hover_message.hover()

            # click reply in thread
            click_reply_in_thread = page.locator('button[aria-label="Reply in thread"]').nth(-1)
            click_reply_in_thread.click()

            # Click reply in thread
            logos_reply_chat = page.locator('button[aria-label="hiiii I am here"]').nth(-1)

            # Get the first child div inside the button
            button_content = logos_reply_chat.locator("div").nth(0)

            # Locate only the direct child divs (first-level children)
            # Use `:scope` to limit to direct children
            outer_divs = button_content.locator(":scope > div").all()

            # Assert that there are exactly two outer divs
            assert len(outer_divs) == 2, f"Expected 2 outer divs, but found {len(outer_divs)}"

            # Hover over the first two outer divs
            for i, child in enumerate(outer_divs[:2]):
                child.hover(timeout=1000)

        except Exception:
            # We re-raise the exception so the test fails, but the trace is still saved
            raise
        finally:
            # Stop tracing and save the trace
            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")

            # Clean the trace
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")

            # Close browser
            browser.close()
