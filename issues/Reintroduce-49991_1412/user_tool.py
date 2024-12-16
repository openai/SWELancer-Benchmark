import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import email
import imaplib
import re
import secrets
import string
import time
from email.header import decode_header

import pytest
from playwright.async_api import Page, TimeoutError, async_playwright, expect

USER_NAME = "xecuycismfsga+49991"
USER_EMAIL = f"{USER_NAME}@gmail.com"
PASSWORD = "uwgb zzoc cofa kaaq"
NOW = int(time.time())


def get_magic_code(
    user_email: str, password: str, current_timestamp: int, retries=5, delay=3
):
    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    imap.login(user_email, password)

    for _attempt in range(retries):
        print(f"Attempt {_attempt}")
        
        # Don't wait on the first attempt
        if _attempt > 0:
            print(f"Waiting {delay} seconds before next attempt...")
            time.sleep(delay)
        
        imap.select("inbox")
        status, messages = imap.search(
            None, '(UNSEEN SUBJECT "Expensify magic sign-in code:")'
        )

        if status == "OK":
            email_ids = messages[0].split()

            if email_ids:
                latest_email_id = email_ids[-1]
                status, msg_data = imap.fetch(latest_email_id, "(RFC822)")

                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])

                        # Get email timestamp and convert to UTC
                        email_date = msg.get("Date")
                        email_timestamp = email.utils.mktime_tz(
                            email.utils.parsedate_tz(email_date)
                        )

                        # Convert current_timestamp to UTC
                        current_utc = time.time()

                        # Mark the email as seen so we don't process it again
                        imap.store(latest_email_id, "+FLAGS", "\\Seen")

                        print(
                            f"Email time: {email_timestamp}, Current time: {current_utc}"
                        )

                        # If email is too old, wait and try again
                        if email_timestamp < current_timestamp:
                            print(
                                f"Found old email from {email_date}, waiting for new one..."
                            )
                            break  # Break the response_part loop

                        subject, encoding = decode_header(msg["Subject"])[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding or "utf-8")

                        match = re.search(
                            r"Expensify magic sign-in code: (\d+)", subject
                        )
                        if match:
                            code = match.group(1)
                            imap.logout()
                            return code

    imap.logout()
    print("Max retries reached. Email not found.")
    return None


def generate_random_string(length=12):
    # Generate a random base64 string
    random_bytes = secrets.token_bytes(length)
    base64_string = secrets.base64.b64encode(random_bytes).decode("utf-8")

    # Filter to include only alphanumeric characters
    alphanumeric_string = "".join(
        filter(lambda x: x in string.ascii_letters + string.digits, base64_string)
    )

    # Return the first `length` characters of the filtered string
    return alphanumeric_string[:length]


async def login_or_create_user(page: Page, user_email: str, password: str):
    await page.get_by_test_id("username").fill(user_email)
    await page.get_by_role("button", name="Continue").click()

    try:
        await page.get_by_role("button", name="Join").wait_for(
            state="visible", timeout=2000
        )
        firstname, lastname = generate_random_string(6), generate_random_string(6)
        await create_user(page, firstname, lastname)
    except TimeoutError:
        await login(page, user_email, password)

    await page.get_by_label("Inbox").wait_for(state="visible", timeout=5000)


async def login(page: Page, user_email: str, password: str):
    # magic_code = get_magic_code(user_email, password, NOW, retries=3, delay=3)
    magic_code = "111111"
    await page.get_by_role("textbox").fill(magic_code)


async def create_user(page: Page, firstname: str, lastname: str):
    await page.get_by_role("button", name="Join").click()

    # Update profile
    await page.get_by_text("Track and budget expenses").click()
    await page.get_by_role("textbox", name="First name").fill(firstname)
    await page.get_by_role("textbox", name="Last name").fill(lastname)
    await page.get_by_role("button", name="Continue").click()

    await page.get_by_label("Back").first.click()
    await close_button_if_present(page)


async def leave_group_chat(page: Page):
    if await page.get_by_text(USER_NAME).first.is_visible():
        print("Leaving group chat")

        # Open group details
        await page.get_by_text(USER_NAME).first.click()
        await page.locator(
            f'div[data-testid="DisplayNamesWithTooltip"]:has-text("{USER_NAME}")'
        ).last.click()
        await page.get_by_label("Leave").click()
        await page.get_by_label("Back").first.click()

    else:
        print("No group chat to leave")


async def close_button_if_present(page: Page):
    """
    Occasionally, there is a close button that prevents any clicks on the page as
    it covers most of the screen. This button cannot be seen visually.
    """
    close_button = page.locator('button[aria-label="Close"]')
    count = await close_button.count()

    for i in range(count):
        button = close_button.nth(i)
        if await button.is_visible():
            await button.click()


@pytest.mark.asyncio  # ensure you have pytest-asyncio installed
async def test_delete_task():
    from utils.trace_cleaner import trace_cleaner

    async with async_playwright() as p:
        proxy = {"server": "http://127.0.0.1:8080/"}
        args = ["--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"]
        
        # Launch webkit (safari) and open new page
        browser = await p.chromium.launch(
            headless=True, slow_mo=500, proxy=proxy, args=args
        )  # Adds 1 second delay between actions
        phone = p.devices["Galaxy S9+"]
        context = await browser.new_context(**phone)

        # Start tracing
        await context.tracing.start(title="test_delete_task", screenshots=True, snapshots=True, sources=True)
        page = await context.new_page()
        try:
            # login
            await page.goto("https://dev.new.expensify.com:8082/")
            await login_or_create_user(page, USER_EMAIL, PASSWORD)

            # Disable focus mode (we need all chats to be visible)
            await page.get_by_label("My settings").click()
            await page.get_by_label("Preferences").click()
            await page.get_by_text("Priority mode").click()
            await page.get_by_test_id("selection-list").get_by_label("Most recent").click()
            await page.get_by_label("Back").first.click()
            await page.get_by_label("Inbox").click()
            await close_button_if_present(page)
            # Leave group chat if present
            await leave_group_chat(page)

            # create group chat
            await close_button_if_present(page)
            await page.get_by_label("Start chat (Floating action)").click()
            await page.get_by_label("Start chat", exact=True).click()
            for user_email in [
                f"{USER_NAME}_0@gmail.com",
                f"{USER_NAME}_1@gmail.com",
            ]:
                await page.get_by_test_id("selection-list-text-input").fill(user_email)
                await page.get_by_role("button", name="Add to group").click()
            await page.get_by_role("button", name="Next").click()
            await page.get_by_role("button", name="Start group").click()
            await page.get_by_label("Back").first.click()
            await page.get_by_label("Inbox").wait_for(state="visible")
            await page.reload()

            # Create task
            await page.get_by_text(USER_NAME).first.click()
            await page.get_by_label("Create").last.click()
            await page.get_by_label("Assign task").click()
            await page.get_by_role("textbox", name="Title").fill("Title")
            await page.get_by_role("button", name="Next").click()
            await page.get_by_role("button", name="Confirm task").click()

            # Open task details
            await page.get_by_role("button", name="Task").last.click()

            # Open task menu (click on task header)
            await page.locator(
                'div[data-testid="DisplayNamesWithTooltip"]:has-text("Title")'
            ).click()

            # Delete the task
            await page.get_by_test_id("ReportDetailsPage").get_by_label("Delete").click()
            await page.get_by_role("button", name="Delete").click()
            await page.wait_for_timeout(1000)

            await page.get_by_role("button", name="Back").click()
            await expect(page.get_by_text("[Deleted task]").first).not_to_be_visible()

            await leave_group_chat(page)
        finally:
            # Stop tracing and clean
            await context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            # Close context/browser
            await context.close()
            await browser.close()
