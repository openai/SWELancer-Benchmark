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
from utils.trace_cleaner import trace_cleaner

USER_EMAIL = "xecuycismfsga+50163@gmail.com"
PASSWORD = "uwgb zzoc cofa kaaq"
SEARCH_LABEL = "type:expense status:all category:none currency:AED expenseType:cash"
SLOW_MO: float | None = 500
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
    return "123456"


async def create_user(page: Page, firstname: str, lastname: str):
    await page.get_by_role("button", name="Join").click()

    # Update profile
    await page.get_by_text("Track and budget expenses").click()
    await page.get_by_role("textbox", name="First name").fill(firstname)
    await page.get_by_role("textbox", name="Last name").fill(lastname)
    await page.get_by_role("button", name="Continue").click()


async def login(page: Page, user_email: str, password: str):
    # get current timestamp
    magic_code = get_magic_code(user_email, password, NOW, retries=3, delay=5)
    await page.get_by_role("textbox").fill(magic_code)
    await page.get_by_label("Inbox").wait_for(state="visible")


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


def split_string_in_half(input_string: str):
    half = len(input_string) // 2
    return input_string[:half], input_string[half:]


async def delete_search(page: Page):
    # delete search
    try:
        await page.locator("#overLayBottomButton").wait_for(
            state="visible", timeout=2000
        )
        await page.locator("#overLayBottomButton").click()  # issue here
    except TimeoutError:
        pass
    await page.get_by_label(SEARCH_LABEL).get_by_label("More").click()
    await page.get_by_label("Delete").click()
    await page.get_by_role("button", name="Delete").click()


async def login_or_create_user(page: Page, user_email: str, password: str):
    await page.get_by_test_id("username").fill(user_email)
    await page.get_by_role("button", name="Continue").click()

    try:
        await page.get_by_role("button", name="Join").wait_for(
            state="visible", timeout=2000
        )
        first_name, last_name = split_string_in_half(generate_random_string())
        await create_user(page, first_name, last_name)
    except TimeoutError:
        await login(page, user_email, password)


@pytest.mark.asyncio  # ensure you have pytest-asyncio installed
async def test_search_clear_button():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True, args=[
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
        ])
        context = await browser.new_context()
        # Start tracing
        await context.tracing.start(screenshots=True, snapshots=True, sources=True)

        try:
            page = await context.new_page()

            await page.goto("https://dev.new.expensify.com:8082/")

            # login or create user
            await login_or_create_user(page, USER_EMAIL, PASSWORD)

            # Navigate to search
            await page.get_by_test_id("CustomBottomTabNavigator").get_by_label(
                "Search"
            ).click()

            # delete search if it exists (clean slate)
            try:
                await page.get_by_label(SEARCH_LABEL).wait_for(
                    state="visible", timeout=3000
                )
                print("Deleting search")
                await delete_search(page)
            except TimeoutError:
                print("Search not found")

            await page.get_by_test_id("SearchPageBottomTab").get_by_label(
                "Expenses"
            ).click()
            await page.get_by_role("button", name="Filters").click()

            items = [
                {"name": "Category", "locator": '[id="No\\ category"]'},
                {"name": "Currency", "locator": '[id="AED\\ -\\ Dhs"]'},
                {"name": "Expense type", "locator": "#Cash"},
            ]

            for item in items:
                await page.get_by_test_id("SearchAdvancedFiltersPage").get_by_role(
                    "menuitem", name=item["name"]
                ).click()
                await page.locator(item["locator"]).click()
                await page.get_by_role("button", name="Save").click()

            await page.get_by_role("button", name="View results").wait_for(
                state="visible", timeout=3000
            )
            await page.get_by_role("button", name="Save search").click()

            # Edit saved search
            element = page.get_by_label(SEARCH_LABEL)
            await element.wait_for(state="visible", timeout=3000)
            await element.get_by_label("More").click()
            await page.get_by_label("Rename").click()
            await expect(page.get_by_label("Clear")).to_be_visible()

            # clear name
            await page.get_by_label("Clear").click()
            await expect(page.get_by_role("textbox", name="Search name")).to_have_value("")
        except Exception as e:
            raise e
        finally:
            # Stop tracing and save the file
            await context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            # Close context/browser
            await context.close()
            await browser.close()
