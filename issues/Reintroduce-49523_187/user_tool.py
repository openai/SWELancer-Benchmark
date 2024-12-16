import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
import imaplib
import logging
import sys
import re
import email
import string, random
import pytest
import pytest_asyncio
from playwright.async_api import async_playwright, expect

from utils.trace_cleaner import trace_cleaner

# Expensify app URL
EXPENSIFY_URL = "https://dev.new.expensify.com:8082/"

# Email login credentials
EMAIL_USERNAME = "naturesv057@gmail.com"
EMAIL_PASSWORD = "hyjk ilxi pnom oret"

# Email username postfix
EMAIL_USERNAME_POSTFIX = "49523_2"

# Logger
logging.basicConfig(level=logging.INFO, stream=sys.stdout, format="%(message)s")
LOGGER = logging.getLogger(__name__)

def generate_user_email(user_id=None):
    """
    Generate an email address for a user login.
    """
    temp = EMAIL_USERNAME.rsplit("@", 1)
    username = temp[0].strip()
    domain = temp[1].strip()
    return f"{username}+{EMAIL_USERNAME_POSTFIX}{user_id or ''}@{domain}"

def clear_inbox(username, password):
    """
    Delete all existing messages from the Inbox.
    """
    LOGGER.info("Deleting all existing messages from the email inbox")
    with imaplib.IMAP4_SSL(host="imap.gmail.com") as imap:
        imap.login(username, password)
        imap.select("inbox")
        imap.store("1:*", "+FLAGS", "\\Deleted")
        imap.expunge()
        imap.close()

def get_otp_from_email(username, password, retries=1, delay=1):
    """
    Read the OTP email and return the OTP code.
    """
    LOGGER.info("Reading the OTP email")
    with imaplib.IMAP4_SSL(host="imap.gmail.com") as imap:
        imap.login(username, password)
        for i in range(1, retries + 1):
            imap.select("inbox")
            status, messages = imap.search(None, "ALL")
            if status == "OK":
                for message_id in reversed(messages[0].split()):
                    status, data = imap.fetch(message_id, "(RFC822)")
                    if status == "OK":
                        email_message = email.message_from_bytes(data[0][1])
                        subject, encoding = email.header.decode_header(email_message["Subject"])[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding)
                        if subject.startswith("Expensify magic sign-in code:"):
                            otp_code = subject.split(":")[-1].strip()
                            LOGGER.info("Got the OTP %s", otp_code)
                            return otp_code
            time.sleep(delay)
        imap.close()
    return "123456"

async def login_user(page, email, first_name="John", last_name="Doe"):
    """
    Login to the Expensify app and complete the onboarding.
    """
    # Clear the email inbox
    clear_inbox(EMAIL_USERNAME, EMAIL_PASSWORD)
    # Open the Expensify app
    await page.goto(EXPENSIFY_URL)
    # Login user
    await page.get_by_test_id("username").fill(email)
    await page.get_by_role("button", name="Continue").click()

    # Get the OTP and complete verification
    otp_code = get_otp_from_email(EMAIL_USERNAME, EMAIL_PASSWORD)
    await page.get_by_test_id("validateCode").fill(otp_code)


async def start_chat_with_new_user(page):
    start_button = page.locator("button[aria-label='Start chat (Floating action)']")
    await expect(start_button).to_be_visible()
    await start_button.click()

    start_chat_div = page.locator("div[role='menuitem'][aria-label='Start chat']")
    await expect(start_chat_div).to_be_visible()
    await start_chat_div.click()

    invite_textbox = page.locator("input[aria-label='Name, email, or phone number']").locator("visible=true")
    await invite_textbox.fill("milan@gmail.com")

    await page.wait_for_timeout(1000)

    user_button = page.locator("button[aria-label='milan@gmail.com']", has_text='milan@gmail.com').last
    await expect(user_button).to_be_visible()
    await user_button.click()


async def select_currency(page, currency: str = "USD", currency_symbol: str = "$"):
    currency_icon = page.locator('button[aria-label="Select a currency"]').last
    await expect(currency_icon).to_be_visible()
    await currency_icon.click()

    search_textbox = page.locator('input[aria-label="Search"]')
    await expect(search_textbox).to_be_visible()
    await search_textbox.fill(currency)

    currency_button = page.locator(f'button[aria-label="{currency} - {currency_symbol}"]').last
    await expect(currency_button).to_be_visible()
    await currency_button.click()


async def pay_to_user(page):
    plus_create_icon = page.locator('button[aria-label="Create"]').last
    await expect(plus_create_icon).to_be_visible()
    await plus_create_icon.click()

    try:
        pay_user_button = page.locator(f'div[aria-label="Pay milan@gmail.com"][role="menuitem"]')
        await expect(pay_user_button).to_be_visible()
        await pay_user_button.click()
    except:
        pay_user_button = page.locator(f'div[aria-label="Pay Hidden"][role="menuitem"]')
        await expect(pay_user_button).to_be_visible()
        await pay_user_button.click()

    await select_currency(page, currency="USD", currency_symbol="$")
    await page.locator('input[role="presentation"]').last.fill("10")

    next_button = page.locator('button[data-listener="Enter"]', has_text="Next").last
    await expect(next_button).to_be_visible()
    await next_button.click()

    pay_elsewhere_button = page.locator('button', has_text="Pay with Expensify")
    await expect(pay_elsewhere_button).to_be_visible()
    await pay_elsewhere_button.click()


async def validate_pay_with_expensify_page(page):

    error_page = page.locator('div[dir="auto"]', has_text="Hmm... it's not here").last
    await expect(error_page).not_to_be_visible()

    try:
        valid_page = page.locator('div[dir="auto"]', has_text="This feature requires you to validate your account.").last
        await expect(valid_page).to_be_visible()
    except:
        expect(page.locator("iframe[title=\"Plaid Link\"]").content_frame.get_by_role("heading", name="Expensify uses Plaid to")).to_be_visible()


@pytest_asyncio.fixture
async def browser_context(headless=True, device=None, geolocation=None):
    # Start Playwright
    playwright = await async_playwright().start()

    # Launch the Chromium browser (headless = False)
    browser = await playwright.chromium.launch(
        headless=True,
        proxy={
            'server': 'http://127.0.0.1:8080',
        },
        args=[
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
        ],
        slow_mo=3000
    )

    # Create browser context and page
    context_args = {}
    if device:
        context_args.update(pw.devices[device])
    if geolocation:
        context_args["geolocation"] = geolocation
        context_args["permissions"] = ["geolocation"]

    context = await browser.new_context(**context_args)
    page = await context.new_page()

    # Set context offline (False)
    await context.set_offline(False)

    yield context, page  # Provide both context and page to the test

    # Cleanup (close the browser and stop Playwright after the test is done)
    await context.close()
    await browser.close()
    await playwright.stop()


@pytest.mark.asyncio
async def test_pay_with_expensify_page(browser_context):
    context, page = browser_context
    trace_path = "/app/expensify/user_tool/output_browser1.zip"
    test_error = None

    # Start tracing
    await context.tracing.start(
        title="test_pay_with_expensify_page",
        screenshots=True,
        snapshots=True,
        sources=True
    )

    try:
        # Step 1: Login user1
        email = generate_user_email()
        LOGGER.info("User email %s", email)
        await login_user(page, email)
        await page.wait_for_timeout(5000)

        LOGGER.info("User logged in successfully")

        await start_chat_with_new_user(page)
        await pay_to_user(page)
        await page.wait_for_timeout(20000)
        await validate_pay_with_expensify_page(page)

    except Exception as e:
        test_error = e
    finally:
        # Stop tracing and export
        await context.tracing.stop()
        await context.tracing.export(trace_path)
        # Clean the trace
        trace_cleaner(trace_path)

    if test_error:
        raise test_error
