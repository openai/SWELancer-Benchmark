import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
import pytest
import pytest_asyncio
from playwright.async_api import async_playwright, expect

from utils.trace_cleaner import trace_cleaner


def generate_random_email():
    return f"test+{1733988243}@turing.com"


async def perform_first_time_user_setup(page):
    phone_or_email_input = page.locator('input[type="email"]')
    await expect(phone_or_email_input).to_be_visible()
    await phone_or_email_input.fill(generate_random_email())

    continue_button = page.locator('button[tabindex="0"]')
    await expect(continue_button).to_be_visible()
    await continue_button.click()
    time.sleep(1)

    try: 
        print("Maybe we need to click again")
        continue_button = page.locator('button[tabindex="0"]')
        await expect(continue_button).to_be_visible()
        await continue_button.click()
    except Exception as e:
        pass

    await expect(page.locator("text=What do you want to do today?")).to_be_visible()

    await page.locator("text='Track and budget expenses'").click()
    time.sleep(1)
        
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
    time.sleep(1)


async def create_expense_in_current_chat(page):
    create = page.locator("button[aria-label='Create']").locator("visible=true")
    await create.click()

    submit_expense = page.locator("div[aria-label='Submit expense'][role='menuitem']").locator("visible=true").get_by_text("Submit expense")
    await expect(submit_expense).to_be_visible()
    await submit_expense.click()
    time.sleep(1)

    await page.keyboard.type("200")
    await page.keyboard.press("Enter")
    await page.keyboard.press("Enter")


async def create_new_expense(page, phone_number="+923211234567"):
    # Find the create chat button
    create_chat_button = page.locator("button[aria-label='Start chat (Floating action)']")
    await expect(create_chat_button).to_be_visible()
    await create_chat_button.click()
    time.sleep(1)

    # Find div with label Submit expense
    submit_expense_option = page.locator("div[aria-label='Submit expense'][role='menuitem']")
    await expect(submit_expense_option).to_be_visible()
    await submit_expense_option.click()
    time.sleep(1)

    # Find button with aria-label Manual
    manual_option = page.locator("button[aria-label='Manual']")
    await expect(manual_option).to_be_visible()
    await manual_option.click()
    time.sleep(1)

    # The input field is auto-focused, so we can pass keys directly
    await page.keyboard.type("100")
    time.sleep(1)

    # Press button with text Next
    await page.keyboard.press("Enter")
    time.sleep(1)

    # Type in random phone number
    await page.keyboard.type(phone_number)
    time.sleep(10)

    # Get div with data-testid selection-list
    selection_list = page.locator("div[data-testid='selection-list']")
    await expect(selection_list).to_be_visible()

    # Find first button in selection list and click on it
    first_button = await selection_list.locator("button").all()
    await expect(first_button[0]).to_be_visible()
    await first_button[0].click()

    # Press the Enter key to perform the Save
    await page.keyboard.press("Enter")
    time.sleep(1)


async def open_search_left_menu(page):
    search = page.locator("button[aria-label='Search']").locator("visible=true")
    await expect(search).to_be_visible()
    await search.click()


async def open_any_expense_in_view(page):
    time.sleep(1)
    while True:
        view_button = await page.locator("button[aria-label]").locator("visible=true").get_by_text("View").all()
        if view_button:
            break
    view_button = view_button[0]
    await expect(view_button).to_be_visible()
    await view_button.click()


async def open_chat_expense_header_top(page):
    time.sleep(2)
    header = page.locator("div[data-testid='DisplayNamesWithTooltip']").locator("visible=true").get_by_text("expense")
    await expect(header).to_be_visible()

    # Get bounding box of the header
    header_bbox = await header.bounding_box()

    # If header is outside the viewport from the left,
    # change the header bbox to the right
    if header_bbox['x'] < 0:
        header_bbox['x'] = 50
        # Perform the click using precise coords
        await page.mouse.click(header_bbox['x'], header_bbox['y'])
    else:
        await header.click(force=True)


async def enable_hold_in_report(page):
    time.sleep(1)
    hold_button = page.locator("button[aria-label]").get_by_text("Hold")
    await expect(hold_button).to_be_visible()

    bbox = await hold_button.bounding_box()
    if bbox['x'] < 0:
        await page.mouse.click(10, bbox['y'])
    else:
        await hold_button.click(force=True)
    time.sleep(1)

    await page.keyboard.type("Hold reason")
    await page.keyboard.press("Enter")
    time.sleep(1)


async def verify_button_in_bottom_right_quarter(page):
    time.sleep(2)
    got_it = page.locator("button[aria-label]").locator("visible=true").get_by_text("Got it")
    await expect(got_it).to_be_visible()

    viewport = page.viewport_size
    button_bbox = await got_it.bounding_box()
    assert is_button_in_bottom_right_quarter(button_bbox, viewport)


def is_button_in_bottom_right_quarter(button_bbox, viewport):
    # Calculate the dimensions of the bottom-right quarter
    quarter_x_start = viewport['width'] / 2
    quarter_y_start = viewport['height'] / 2
    
    # Check if the button is contained within the bottom-right quarter
    is_contained = (
        button_bbox['x'] >= quarter_x_start and
        button_bbox['y'] >= quarter_y_start and
        button_bbox['x'] + button_bbox['width'] <= viewport['width'] and
        button_bbox['y'] + button_bbox['height'] <= viewport['height']
    )
    return is_contained


@pytest_asyncio.fixture
async def browser_context():
    # Start Playwright
    playwright = await async_playwright().start()
    
    # Launch the Chromium browser (headless = False)
    browser = await playwright.chromium.launch(
        headless=True, slow_mo=1000, args=[
            "--ignore-certificate-errors", 
            "--disable-web-security", 
            "--disable-features=IsolateOrigins,site-per-process"]
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
async def test_hold_modal_on_right_in_expense_report_search(browser_context):
    context, page = browser_context  # Unpack the context and page from the fixture

    trace_path = '/app/expensify/user_tool/output_browser1.zip'

    await context.tracing.start(
        title="test_hold_modal_on_right_in_expense_report_search",
        screenshots=True,
        snapshots=True,
        sources=True
    )

    try:
        await page.goto("https://dev.new.expensify.com:8082/")
        await perform_first_time_user_setup(page)
        await create_new_expense(page)
        await create_expense_in_current_chat(page)
        await open_search_left_menu(page)
        await open_any_expense_in_view(page)
        await open_chat_expense_header_top(page)
        await enable_hold_in_report(page)
        await verify_button_in_bottom_right_quarter(page)
    except Exception as e:
        # Re-raise the exception after we stop tracing
        raise e
    finally:
        await context.tracing.stop()
        await context.tracing.export(trace_path)
        trace_cleaner(trace_path)
