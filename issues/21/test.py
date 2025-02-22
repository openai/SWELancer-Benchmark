import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager


def get_user_email():
    return f"nitish.expensify+{103}@gmail.com"


def get_magic_code():
    return "123456"


def login_user(p: PlaywrightContextManager, first_name="John", last_name="Doe"):
    browser = p.chromium.launch(headless=True, args=[
        "--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"],
        slow_mo=1000)

    page = browser.new_page()
    user_email = get_user_email()
    first_name = 'John'
    last_name = 'Doe'


    page.goto('https://dev.new.expensify.com:8082/')


    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()

    try:
        expect(page.get_by_role("button", name="Sign in")).to_be_visible()
        page.get_by_test_id("validateCode").fill(get_magic_code())
    except Exception:
        page.get_by_role("button", name="Join").click()

    try:
        expect(page.locator('div[aria-label="Track and budget expenses"]').nth(0)).to_be_visible()


        page.locator('div[aria-label="Track and budget expenses"]').nth(0).click()


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
    with sync_playwright() as p:

        page = login_user(p)


        click_settings_button = page.locator("[aria-label='My settings']")
        click_settings_button.click()


        click_workspace_button = page.locator("div[aria-label='Workspaces']")
        click_workspace_button.click()


        create_new_workspace_button = page.locator("[aria-label='New workspace']").nth(0)
        create_new_workspace_button.click()


        click_back_button = page.locator("[aria-label='Back']").nth(-1)
        click_back_button.click()


        click_Inbox = page.locator("button[aria-label='Inbox']").nth(-1)
        click_Inbox.click()


        click_WS_chat = page.locator("div", has_text="John Doe's Workspace").nth(-1)
        click_WS_chat.click()


        edit_input_text = page.locator('div[contenteditable="true"]').nth(-1)


        edit_input_text.fill("hiiii I am here")


        send_message = page.locator("[aria-label='Send']")
        send_message.click()


        hover_message = page.locator('div[aria-label="Chat message"]', has_text="hiiii I am here").nth(-1)
        hover_message.hover()


        click_reply_in_thread = page.locator('button[aria-label="Reply in thread"]').nth(-1)
        click_reply_in_thread.click()


        logos_reply_chat = page.locator('button[aria-label="hiiii I am here"]').nth(-1)


        button_content = logos_reply_chat.locator("div").nth(0)



        outer_divs = button_content.locator(":scope > div").all()


        assert len(outer_divs) == 2, f"Expected 2 outer divs, but found {len(outer_divs)}"


        for i, child in enumerate(outer_divs[:2]):
            child.hover(timeout=1000)
