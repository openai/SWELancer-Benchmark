import os
import re

import pytest
from playwright.async_api import Page, TimeoutError, async_playwright, expect

EMAIL_USERNAME = "xecuycismfsga"
EMAIL_ALIAS = "1wagfzgm"
USER_EMAIL = f"{EMAIL_USERNAME}+{EMAIL_ALIAS}@gmail.com"
PASSWORD = "uwgb zzoc cofa kaaq"
SLOW_MO: int | None = 500
PROXY_URL = os.getenv("PROXY_URL")
NEW_DOT_URL = "https://dev.new.expensify.com:8082"


def extract_magic_link(message_body: str):
    # Regular expression to find the URL in the HTML anchor tag
    url_pattern = re.compile(r'<a\s+href=["\']([^"\']+?)["\'][^>]*?>')

    # Search for the pattern in the message body
    match = url_pattern.search(message_body)

    if match:
        # Return the first captured group, which is the URL
        return match.group(1)

    # If no URL is found, return None or some other default value
    return None


def extract_path(url):
    # Split the URL by the scheme and domain
    parts = url.split("https://new.expensify.com")

    # The path is the second element in the list
    if len(parts) > 1:
        return parts[1]

    return None


def replace_last_n_chars(string: str, n: int = 2, replacement_char: str = "*"):
    if n <= 0:
        raise ValueError(
            "The number of characters to replace must be greater than zero."
        )

    if len(string) < n:
        raise ValueError(
            "The input string is shorter than the number of characters to replace."
        )

    return string[:-n] + (replacement_char * n)


def read_magic_link(user_email: str, password: str, retries=5, delay=6):
    """
    Retrieves the Magic Link from unread emails.

    Args:
        retries (int): Number of retries to attempt fetching the OTP code.
        delay (int): Delay in seconds between retries.

    Returns:
        str: The Magic Link if found, else None.
    """
    return f"{NEW_DOT_URL}/v/19171331/3837**"


async def create_user(page: Page, firstname: str = "User", lastname: str = EMAIL_ALIAS):
    await page.get_by_role("button", name="Join").click()

    # Update profile
    await page.get_by_text("Track and budget expenses").click()
    await page.get_by_role("textbox", name="First name").fill(firstname)
    await page.get_by_role("textbox", name="Last name").fill(lastname)
    await page.get_by_role("button", name="Continue").click()


async def attempt_login(page: Page, user_email=USER_EMAIL, password=PASSWORD):
    request_new_link = page.get_by_label("Didn't receive a magic code?")

    await request_new_link.click(timeout=60000)
    # get current timestamp
    magic_link = read_magic_link(user_email, password)

    if magic_link is None:
        raise ValueError("Failed to retrieve magic link")

    await page.goto(magic_link)


async def logout(page: Page):
    await page.get_by_label("My settings").click()
    await page.get_by_label("Sign out").click()


async def login_or_create_user(
    page: Page,
    firstname: str = "User",
    lastname: str = EMAIL_ALIAS,
    user_email: str = USER_EMAIL,
):
    await page.goto(NEW_DOT_URL, timeout=60000)
    await page.get_by_test_id("username").fill(user_email)
    await page.get_by_role("button", name="Continue").click()

    try:
        await page.get_by_role("button", name="Join").wait_for(
            state="visible", timeout=2000
        )
        await create_user(page, firstname, lastname)
        await logout(page)
        await login_or_create_user(page, firstname, lastname, user_email)
    except TimeoutError:
        await attempt_login(page)


@pytest.mark.asyncio
async def test_scroll_to_comments():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            proxy={"server": PROXY_URL} if PROXY_URL else None,
            headless=False,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--ignore-certificate-errors",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
            ],
            slow_mo=SLOW_MO,
        )

        context = await browser.new_context()
        page = await context.new_page()

        # admin login
        await login_or_create_user(page)

        await expect(
            page.get_by_text("Hmm... it's not here", exact=True)
        ).to_be_visible()

        # Close all tabs and browser
        await page.close()
        await context.close()
        await browser.close()
