import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
import pytest
import pytest_asyncio

from playwright.async_api import async_playwright, expect
from utils.trace_cleaner import trace_cleaner


def generate_random_email():
    return f"newuser12+{49523}@gmail.com"


async def perform_first_time_user_setup(page):
    phone_or_email_input = page.locator('input[type="email"]')
    await expect(phone_or_email_input).to_be_visible()
    await phone_or_email_input.fill(generate_random_email())

    continue_button = page.locator('button[tabindex="0"]')
    await continue_button.click()

    continue_button = page.locator('button[tabindex="0"]', has_text="Join")
    # await expect(continue_button).to_be_visible()
    await continue_button.click()

    await page.wait_for_timeout(5000)

    await expect(page.locator("text=What do you want to do today?")) .to_be_visible()

    await page.locator("text='Track and budget expenses'").click()
        
    # Find first name using aria-label, click on it and add a first name
    first_name_input = page.locator('input[aria-label="First name"]')
    await expect(first_name_input).to_be_visible()
    await first_name_input.fill("Test")

    # Find last name using aria-label, click on it and add a last name
    last_name_input = page.locator('input[aria-label="Last name"]')
    await expect(last_name_input).to_be_visible()
    await last_name_input.fill("User")

    # Find Continue button using text and click on it
    continue_button = page.locator("text=Continue")
    await expect(continue_button).to_be_visible()
    await continue_button.click()


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

    valid_page = page.locator('div[dir="auto"]', has_text="This feature requires you to validate your account.").last
    await expect(valid_page).to_be_visible()


@pytest_asyncio.fixture
async def browser_context():
    # Start Playwright
    playwright = await async_playwright().start()
    
    # Launch the Chromium browser (headless = False)
    browser = await playwright.chromium.launch(headless=True, slow_mo=500, args=[
                    "--disable-web-security",
                    "--disable-features=IsolateOrigins,site-per-process",]
                    )
    
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
async def test_pay_with_expensify_page(browser_context):
    context, page = browser_context  # Unpack the context and page from the fixture

    trace_path = "/app/expensify/user_tool/output_browser1.zip"
    await context.tracing.start(screenshots=True, snapshots=True, sources=True)
    try:
        await page.goto("https://dev.new.expensify.com:8082/")
        await perform_first_time_user_setup(page)
        await start_chat_with_new_user(page)
        await pay_to_user(page)
        await validate_pay_with_expensify_page(page)
    except Exception as e:
        raise e
    finally:
        await context.tracing.stop()
        await context.tracing.export(path=trace_path)
        trace_cleaner(trace_path)
