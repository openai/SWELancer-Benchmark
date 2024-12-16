import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import email
import imaplib
import os
import re
import time
from email.header import decode_header

import pytest
from playwright.async_api import (
    Page,
    Playwright,
    TimeoutError,
    async_playwright,
    expect,
)

from utils.trace_cleaner import trace_cleaner

NOW = int(time.time())
USER_EMAIL = "xecuycismfsga+k7gse6h@gmail.com"
PARTICIPANT_EMAILS = [
    "xecuycismfsga+eawdvh@gmail.com",
    "xecuycismfsga+nzfgxzu@gmail.com",
]
PASSWORD = "uwgb zzoc cofa kaaq"
SLOW_MO = 1000
CACHED: bool = True
PROXY_URL = os.getenv("PROXY_URL")


def get_magic_code(
    user_email: str,
    password: str,
    current_timestamp: int,
    retries=5,
    delay=3,
    slow_mo: int | None = None,  # Add slow_mo parameter
    cached: bool = False,
):
    if cached:
        return "123456"
    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    imap.login(user_email, password)

    additional_delay = (slow_mo / 1000) if slow_mo else 0
    total_delay = delay + additional_delay

    for _attempt in range(retries):
        print(f"Attempt {_attempt}")

        # Don't wait on the first attempt
        if _attempt > 0:
            print(f"Waiting {total_delay} seconds before next attempt...")
            time.sleep(total_delay)

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


async def create_user(page: Page, firstname: str, lastname: str):
    await page.get_by_role("button", name="Join").click()

    try:
        # Update profile
        onboarding = page.get_by_text("Track and budget expenses")
        await onboarding.wait_for(state="visible", timeout=2000)

        await onboarding.click()
        await page.get_by_role("textbox", name="First name").fill(firstname)
        await page.get_by_role("textbox", name="Last name").fill(lastname)
        await page.get_by_role("button", name="Continue").click()
    except TimeoutError:
        pass


async def login(
    page: Page,
    user_email: str,
    password: str,
    slow_mo: int | None = None,
    cached: bool = False,
):
    # get current timestamp
    magic_code = get_magic_code(
        user_email, password, NOW, retries=3, delay=5, slow_mo=slow_mo, cached=cached
    )

    if magic_code is None:
        raise ValueError("Failed to retrieve magic code")
    await page.get_by_role("textbox").fill(magic_code)


async def login_or_create_user(
    page: Page,
    first_name: str = "John",
    last_name: str = "Doe",
    user_email: str = USER_EMAIL,
    password: str = PASSWORD,
    slow_mo: int | None = None,
    cached: bool = False,
):
    await page.get_by_test_id("username").fill(user_email)
    await page.get_by_role("button", name="Continue").click()

    try:
        await page.get_by_role("button", name="Join").wait_for(
            state="visible", timeout=2000
        )
        await create_user(page, first_name, last_name)
    except TimeoutError:
        await login(page, user_email, password, slow_mo, cached=cached)


async def run(playwright: Playwright) -> None:
    browser = await playwright.chromium.launch(
        headless=True,
        slow_mo=SLOW_MO,
        proxy={"server": PROXY_URL} if PROXY_URL else None,
        args=[
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
        ],
    )
    context = await browser.new_context()

    # Start tracing before test logic
    await context.tracing.start(screenshots=True, snapshots=True, title="test_welcome_group_message")

    try:
        page = await context.new_page()

        # Navigate to the page and sign in
        await page.goto("https://dev.new.expensify.com:8082/")
        await login_or_create_user(page, slow_mo=SLOW_MO, cached=CACHED)

        has_text = (
            f':has-text("{PARTICIPANT_EMAILS[0]}"):has-text("{PARTICIPANT_EMAILS[1]}")'
        )
        group_chat = (
            page.get_by_test_id("BaseSidebarScreen")
            .locator(f'button[aria-label="Navigates to a chat"]{has_text}')
            .first
        )
        group_details = page.locator(
            f'div[data-testid="DisplayNamesWithTooltip"]{has_text}'
        ).last

        try:
            # Leave group chat if it exists
            await group_chat.wait_for(state="visible", timeout=3000)
            await group_chat.click()

            # Leave group
            await group_details.click()
            await page.get_by_label("Leave").click()
            await page.get_by_label("Back").last.click()  # Go back home
        except TimeoutError:
            pass

        # Start new group chat with the two participants
        await page.get_by_label("Start chat (Floating action)").click()
        await page.get_by_text("Start chat").click()

        for user_email in PARTICIPANT_EMAILS:
            await page.get_by_test_id("selection-list-text-input").fill(user_email)
            await (
                page.get_by_label(user_email)
                .get_by_role("button", name="Add to group")
                .click()
            )

        await page.locator("button").filter(has_text="Next").click()
        await page.get_by_role("button", name="Start group").click()

        # Check group member details
        await group_details.click()
        await page.get_by_text("Members").click()
        await page.reload()

        # Remove second participant
        await (
            page.get_by_test_id("selection-list")
            .get_by_label(PARTICIPANT_EMAILS[1])
            .first.click()
        )
        await page.get_by_role("button", name="Remove from group").click()
        await page.get_by_role("button", name="Remove", exact=True).click()

        # Go back to the group chat
        await page.get_by_test_id("ReportParticipantsPage").get_by_label("Back").click()
        await page.get_by_test_id("ReportDetailsPage").get_by_label("Back").click()

        # check the welcome message, user should not be part of the message
        welcome_message = (
            page.get_by_test_id("report-actions-list")
            .locator('div:has-text("This chat is with")')
            .last
        )
        await expect(welcome_message).not_to_have_text(PARTICIPANT_EMAILS[1])

        # Clean up / Leave group
        group_details = page.locator(
            f'div[data-testid="DisplayNamesWithTooltip"]:has-text("{PARTICIPANT_EMAILS[0]}")'
        ).last
        await group_details.last.click()
        await page.get_by_label("Leave").click()
    except Exception as e:
        # Re-raise so the test fails properly
        raise e
    finally:
        # Stop and export the trace
        await context.tracing.stop()
        trace_path = "/app/expensify/user_tool/output_browser1.zip"
        await context.tracing.export(path=trace_path)
        trace_cleaner(trace_path)

    await context.close()
    await browser.close()


@pytest.mark.asyncio
async def test_welcome_group_message():
    async with async_playwright() as playwright:
        await run(playwright)
