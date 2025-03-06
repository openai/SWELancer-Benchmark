import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import pytest_asyncio
import re
import time
import email
import pytest
import imaplib
from email.header import decode_header
from playwright.async_api import async_playwright, expect
from datetime import datetime, timezone

MAX_TRIES = 10
USERNAME = "expensify31+1943@gmail.com"

PASSWORD = ""

async def get_magic_code(user_email, password, retries=10, delay=10, since=None):
    if since is None:
        since = datetime.now(timezone.utc).replace(second=0, microsecond=0)

    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    imap.login(user_email, password)

    for attempt in range(retries):


        imap.select("inbox")
        status, messages = imap.search(None, '(UNSEEN SUBJECT "Expensify magic sign-in code:")')

        if status == "OK":
            email_ids = messages[0].split()

            if email_ids:
                latest_email_id = email_ids[-1]
                status, msg_data = imap.fetch(latest_email_id, "(RFC822)")

                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        subject, encoding = decode_header(msg["Subject"])[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding or "utf-8")


                        match = re.search(r"Expensify magic sign-in code: (\d+)", subject)
                        if match:
                            code = match.group(1)
                            imap.logout()
                            return code
            else:
                print("No unread emails found with the subject. Retrying...")
        else:
            print("Failed to retrieve emails. Retrying...")


        time.sleep(delay)

    imap.logout()
    print("Max retries reached. Email not found.")
    return None


async def perform_first_time_user_setup(page):
    login_time = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    phone_or_email_input = page.locator('input[type="email"]')
    await expect(phone_or_email_input).to_be_visible()
    await phone_or_email_input.fill(USERNAME)

    continue_button = page.locator('button[tabindex="0"]')
    await expect(continue_button).to_be_visible()
    await continue_button.click()

    join_button = page.locator('button[tabindex="0"]', has_text="Join")
    if (await join_button.is_visible()):
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

    else:

        await page.wait_for_timeout(3000)

        otp = '123456'


        await page.wait_for_timeout(5000)
        validate_code_input = page.locator('input[autocomplete="one-time-code"]')
        await expect(validate_code_input).to_be_visible()
        await validate_code_input.fill(otp)


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


async def invite_multiple_users_to_workspace(page):
    more_features = page.locator("div[aria-label='Members'][role='menuitem']").locator("visible=true").get_by_text("Members")
    await expect(more_features).to_be_visible()
    await more_features.click()

    invite_member_button = page.locator("button[data-tag='pressable']", has_text="Invite member").locator("visible=true")
    await expect(invite_member_button).to_be_visible()
    await invite_member_button.click()

    invite_textbox = page.locator("input[aria-label='Name, email, or phone number']").locator("visible=true")
    await invite_textbox.fill("abcd@gmail.com")

    user_button = page.locator("button[aria-label='abcd@gmail.com']", has_text='abcd@gmail.com').locator("visible=true")
    await expect(user_button).to_be_visible()
    await user_button.click()

    invite_textbox = page.locator("input[aria-label='Name, email, or phone number']").locator("visible=true")
    await invite_textbox.fill("abcd1@gmail.com")

    user_button = page.locator("button[aria-label='abcd1@gmail.com']", has_text='abcd1@gmail.com').locator("visible=true")
    await expect(user_button).to_be_visible()
    await user_button.click()

    next_button = page.locator("button[data-tag='pressable']", has_text='Next').locator("visible=true").last
    await expect(next_button).to_be_visible()
    await next_button.click()

    invite_button = page.locator("button[data-tag='pressable']", has_text='Invite').locator("visible=true").last
    await expect(invite_button).to_be_visible()
    await invite_button.click()

    back_button = page.locator("button[aria-label='Back']").locator("visible=true").last
    await expect(back_button).to_be_visible()
    await back_button.click()


async def validate_correct_chat_name_visible(page):
    inbox_page = page.locator("button[aria-label='Inbox']")
    await expect(inbox_page).to_be_visible()
    await inbox_page.click()

    await page.wait_for_timeout(5000)

    chat_button = page.locator('button[aria-label="Navigates to a chat"]', has_text="Test User's Workspace").last
    await expect(chat_button).to_be_visible()


    account_settings_button = page.locator("button[aria-label='My settings']")
    await expect(account_settings_button).to_be_visible()
    await account_settings_button.click()
    
    troubleshoot = page.locator("div[role='menuitem'][aria-label='Troubleshoot']").get_by_text("Troubleshoot")
    await expect(troubleshoot).to_be_visible()
    await troubleshoot.click()

    clear_cache = page.locator("div[aria-label='Clear cache and restart']")
    await expect(clear_cache).to_be_visible()
    await clear_cache.click()

    clear_cache_confirmation = page.locator("button", has_text="Reset and refresh")
    await expect(clear_cache_confirmation).to_be_visible()
    await clear_cache_confirmation.click()


    inbox_page = page.locator("button[aria-label='Inbox']")
    await expect(inbox_page).to_be_visible()
    await inbox_page.click()

    await page.wait_for_timeout(2000)

    chat_button = page.locator('button[aria-label="Navigates to a chat"]', has_text="Test User's Workspace").last
    await expect(chat_button).to_be_visible()

    chat_button = page.locator('button[aria-label="Navigates to a chat"]', has_text="Chat Report").last
    await expect(chat_button).not_to_be_visible()


@pytest_asyncio.fixture
async def browser_context():

    playwright = await async_playwright().start()
    

    browser = await playwright.chromium.launch(
            channel="chrome",
            headless=True,
            args=[
                "--ignore-certificate-errors",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process"
            ],
            proxy={"server": "http://localhost:8080"},
            slow_mo=700
        )
    

    context = await browser.new_context()
    page = await context.new_page()
    

    await context.set_offline(False)
    
    yield context, page  # Provide both context and page to the test
    

    await context.close()
    await browser.close()
    await playwright.stop()


@pytest.mark.asyncio
async def test_tags_disabled_button(browser_context):
    context, page = browser_context  # Unpack the context and page from the fixture
    await page.goto("https://dev.new.expensify.com:8082/")
    
    await perform_first_time_user_setup(page)
    await open_account_settings(page)
    await open_workspaces_in_account_settings(page)
    await create_workspace(page)
    await invite_multiple_users_to_workspace(page)
    await validate_correct_chat_name_visible(page)
