import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import pytest
import pytest_asyncio

from playwright.async_api import async_playwright, expect
from utils.email_handler import get_specific_derived_email
from utils.login import NEW_DOT_URL
from utils.trace_cleaner import trace_cleaner

BASE_EMAIL = 'testuserexpensify@gmail.com'
PROXY_SERVER = 'http://127.0.0.1:8080'
FIXED_RANDOM_SUFFIX = '931210'


async def perform_first_time_user_setup(page, email):
    phone_or_email_input = page.locator('input[type="email"]')
    await expect(phone_or_email_input).to_be_visible()
    await phone_or_email_input.fill(email)

    continue_button = page.locator('button[tabindex="0"]')
    await expect(continue_button).to_be_visible()
    await continue_button.click()

    continue_button = page.locator('button[tabindex="0"]', has_text="Join")
    await expect(continue_button).to_be_visible()
    await continue_button.click()

    await expect(page.locator("text=What do you want to do today?")).to_be_visible()

    await page.locator("text='Track and budget expenses'").click()


    first_name_input = page.locator('input[aria-label="First name"]')
    await expect(first_name_input).to_be_visible()
    await first_name_input.fill("Test")


    last_name_input = page.locator('input[aria-label="Last name"]')
    await expect(last_name_input).to_be_visible()
    await last_name_input.fill("User")


    continue_button = page.locator("text=Continue")
    await expect(continue_button).to_be_visible()
    await continue_button.click()


async def open_account_settings(page):
    account_settings_button = page.locator("button[aria-label='My settings']")
    await expect(account_settings_button).to_be_visible()
    await account_settings_button.click()


async def open_workspaces_in_account_settings(page):
    workspace = page.locator("div[role='menuitem'][aria-label='Workspaces']").get_by_text("Workspaces")
    await expect(workspace).to_be_visible()
    await workspace.click()


async def create_workspace(page):
    create_workspace_button = await page.locator("button[aria-label='New workspace']").locator("visible=true").get_by_text("New workspace").all()
    create_workspace_button = create_workspace_button[0]
    await expect(create_workspace_button).to_be_visible()
    await create_workspace_button.click()


async def get_invite_member_to_workspace_link(page):
    more_features = page.locator("div[aria-label='Members'][role='menuitem']").locator("visible=true").get_by_text("Members")
    await expect(more_features).to_be_visible()
    await more_features.click()

    invite_button = page.locator("button[data-tag='pressable']", has_text="Invite member").locator("visible=true")
    await expect(invite_button).to_be_visible()
    await invite_button.click()

    invite_textbox = page.locator("input[aria-label='Name, email, or phone number']").locator("visible=true")
    await invite_textbox.fill("abcd@gmail.com")

    user_button = page.locator("button[aria-label='abcd@gmail.com']", has_text='abcd@gmail.com').locator("visible=true")
    await expect(user_button).to_be_visible()
    await user_button.click()

    next_button = page.locator("button[data-tag='pressable']", has_text='Next').locator("visible=true").last
    await expect(next_button).to_be_visible()
    await next_button.click()

    invite_link = page.url

    invite_button = page.locator("button[data-tag='pressable']", has_text='Invite').locator("visible=true").last
    await expect(invite_button).to_be_visible()
    await invite_button.click()

    return invite_link


async def chat_with_invited_user(page, message=""):
    await page.get_by_label('Back').click()

    inbox_button = page.locator("button[aria-label='Inbox']")
    await expect(inbox_button).to_be_visible()
    await inbox_button.click()

    start_button = page.locator("button[aria-label='Start chat (Floating action)']")
    await expect(start_button).to_be_visible()
    await start_button.click()

    start_chat_div = page.locator("div[role='menuitem'][aria-label='Start chat']")
    await expect(start_chat_div).to_be_visible()
    await start_chat_div.click()

    invite_textbox = page.locator("input[aria-label='Name, email, or phone number']")
    await invite_textbox.fill("abcd@gmail.com")

    user_button = page.get_by_test_id('selection-list').locator('button:has-text("abcd@gmail.com")')
    await expect(user_button).to_be_visible()
    await user_button.click()

    message_textbox = page.get_by_role("textbox")
    await expect(message_textbox).to_be_visible()
    await message_textbox.fill(message)
    await message_textbox.press("Enter")

    my_message = page.locator(f"div[aria-label='{message}']", has_text=message)
    await expect(my_message).to_be_visible()
    await my_message.click()


async def validate_invite_panel_is_visible(page):
    invite_textbox = page.locator("input[aria-label='Name, email, or phone number']")
    await expect(invite_textbox).to_be_visible()


@pytest_asyncio.fixture
async def browser_context():

    playwright = await async_playwright().start()


    browser = await playwright.chromium.launch(
        slow_mo=650,
        headless=True,
        proxy={
            'server': PROXY_SERVER
        },
        args=[
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process'
        ]
    )


    context = await browser.new_context(ignore_https_errors=True)
    page = await context.new_page()


    await context.set_offline(False)

    yield context, page  # Provide both context and page to the test


    await context.close()
    await browser.close()
    await playwright.stop()


@pytest.mark.asyncio
async def test_tags_disabled_button(browser_context):
    context, page = browser_context  # Unpack the context and page from the fixture
    trace_path = "/app/expensify/user_tool/output_browser1.zip"

    await context.tracing.start(
        title="test_tags_disabled_button",
        screenshots=True,
        snapshots=True,
        sources=True
    )

    try:
        await page.goto(NEW_DOT_URL)
        email = get_specific_derived_email(BASE_EMAIL, FIXED_RANDOM_SUFFIX)
        await perform_first_time_user_setup(page, email)
        await open_account_settings(page)
        await open_workspaces_in_account_settings(page)
        await create_workspace(page)
        invite_link = await get_invite_member_to_workspace_link(page)
        await chat_with_invited_user(page, invite_link)

        await page.wait_for_timeout(2000)
        await validate_invite_panel_is_visible(page)

    except Exception as e:
        raise e
    finally:
        await context.tracing.stop()
        await context.tracing.export(trace_path)
        trace_cleaner(trace_path)
