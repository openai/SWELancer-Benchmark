import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import email
import imaplib
import time
import pytest
import pytest_asyncio
from email.header import decode_header
import re
from playwright.async_api import async_playwright, expect

USER_EMAIL = "aliceoglualice@gmail.com"
PASSWORD = "cfpy ofxm lcmq aeta"
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


async def perform_first_time_user_setup(page):
    phone_or_email_input = page.locator('input[type="email"]')
    await expect(phone_or_email_input).to_be_visible()
    await phone_or_email_input.fill(USER_EMAIL)

    continue_button = page.locator('button[tabindex="0"]')
    await expect(continue_button).to_be_visible()
    await continue_button.click()

    try:
        continue_button = page.locator('button[tabindex="0"]', has_text="Join")
        await expect(continue_button).to_be_visible()
        await continue_button.click()
        await expect(page.locator("text=What do you want to do today?")).to_be_visible()

        await page.locator("text='Track and budget expenses'").click(timeout=5000)
            
        # Find first name using aria-label, click on it and add a first name
        first_name_input = page.locator('input[aria-label="First name"]')
        await expect(first_name_input).to_be_visible()
        await first_name_input.fill("Test", timeout=5000)

        # Find last name using aria-label, click on it and add a last name
        last_name_input = page.locator('input[aria-label="Last name"]')
        await expect(last_name_input).to_be_visible()
        await last_name_input.fill("User",timeout=5000)

        # Find Continue button using text and click on it
        continue_button = page.locator("text=Continue")
        await expect(continue_button).to_be_visible()
        await continue_button.click(timeout=5000)
    except:
        magic_code = "123456" #get_magic_code(USER_EMAIL, PASSWORD, NOW, retries=3, delay=3)
        await page.get_by_role("textbox").fill(magic_code)


async def send_message_in_personal_chal(page):
    personal_chat = page.get_by_text(f"Test User (you)")
    await expect(personal_chat).to_be_visible()
    await personal_chat.click()

    message_textbox = page.get_by_role("textbox").last
    await expect(message_textbox).to_be_visible()
    await message_textbox.fill("My Message")

    message_textbox = page.get_by_role("textbox").last
    await expect(message_textbox).to_be_visible()
    await message_textbox.press("Enter")


async def validate_context_menu_opening(page):
    emoji_div = page.locator('div[aria-label="Emoji"][data-tag="pressable"]').last
    await expect(emoji_div).to_be_visible()
    await emoji_div.click()

    message = page.locator('span', has_text="My Message").last
    await expect(message).to_be_visible()
    await message.click(button="right")

    await page.wait_for_timeout(1000)

    option_menu = page.locator('div[aria-label="Reply in thread"]', has_text="Reply in thread").last
    await expect(option_menu).to_be_visible()


@pytest_asyncio.fixture
async def browser_context():
    # Start Playwright
    playwright = await async_playwright().start()
    
    # Launch the Chromium browser (headless = False)
    browser = await playwright.chromium.launch(headless=True, args=[
        "--disable-web-security",
        "--disable-features=IsolateOrigins,site-per-process",
        "--ignore-certificate-errors"
        ])
    # Create browser context and page
    context = await browser.new_context()
    page = await context.new_page()
    
    # Set context offline (False)
    await context.set_offline(False)
    
    yield context, page  # Provide both context and page to the test
    
    # Cleanup (close the browser and stop Playwright after the test is done)
    await context.close()
    await browser.close()
    await playwright.stop()


@pytest.mark.asyncio
async def test_context_menu_opening_on_right_click(browser_context):
    context, page = browser_context  # Unpack the context and page from the fixture
    await page.goto("https://dev.new.expensify.com:8082/")
    
    await perform_first_time_user_setup(page)
    await send_message_in_personal_chal(page)
    await validate_context_menu_opening(page)

