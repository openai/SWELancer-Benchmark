import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import pytest
import pytest_asyncio
import os
from playwright.async_api import async_playwright, expect, Page, BrowserContext
from typing import AsyncGenerator

# Define global parameters
BROWSER_TYPE: str = "chromium"
PLATFORM: str = "desktop"
DATA_DIR: str | None = f"{BROWSER_TYPE}_{PLATFORM}_context"


@pytest.fixture
def config() -> dict[str, str | None]:
    """
    Encapsulate constants into a fixture.
    """
    return {
        "BROWSER_TYPE": BROWSER_TYPE,
        "PLATFORM": PLATFORM,
        "DATA_DIR": DATA_DIR,
    }

def store_email_in_file(file_path: str, email: str):
    with open(file_path, "w") as file:
        file.write(email)


def get_email_from_file(file_path: str):
    with open(file_path, "r") as file:
        return file.read()


async def login_user_if_not_logged_in(
    page: Page,first_name="Asaad", last_name="I"):
    # Launch chromiun and open ne   w page
    await page.bring_to_front()

    # Step 1: Open expensify url
    await page.goto("https://dev.new.expensify.com:8082/home")

    try:
        # If the user is not logged in, the email input should be visible
        await expect(page.locator('input[type="email"]')).to_be_visible(timeout=3000)
    except:
        # If the user is already logged in, do nothing
        return get_email_from_file(DATA_DIR + "_email.txt")

    email = "expensify66+10031@gmail.com"
    store_email_in_file(DATA_DIR + "_email.txt", email)

    # Step 3: Enter email and click continue
    await page.locator('input[type="email"]').fill(email)
    await page.locator("button", has_text="Continue").click()

    # Step 4: Click join button
    await page.locator("button", has_text="Join").click()

    # Step 5: Select 'Track and budget expenses' in onobarding page and click Continue
    # wait for the text to be visible
    await page.locator("text='Track and budget expenses'").wait_for()
    await page.locator("text='Track and budget expenses'").click()
    await page.get_by_role("button", name="Continue").click()

    # Step 6: Enter first name, last name and click continue
    await page.locator('input[name="fname"]').fill(first_name)
    await page.locator('input[name="lname"]').fill(last_name)
    await page.get_by_role("form").get_by_role("button", name="Continue").click()

    # Step 7: Wait for the onboarding process to complete,
    # this can be crucial to avoid any flakiness in the test
    await page.get_by_label("Last chat message preview").filter(
        has_text="task for Track an expense"
    ).click()
    await page.get_by_label("guided-setup-track-personal-").wait_for()
    # For Narrow layout, click on Back button to navigate to inbox
    if PLATFORM.lower() == "mobile":
        await page.get_by_label("Back").click()
        await page.get_by_label("Inbox").wait_for()
        if await page.get_by_label("Close").count() == 1:
            await page.get_by_label("Close").click()
    return email


async def start_chat(page, email="expensify66+1@gmail.com", account_name="Asaad I"):
    # Find the create chat button
    await page.get_by_label("Start chat (Floating action)").click()

    await page.get_by_label("Start chat", exact=True).click()

    await page.get_by_test_id("NewChatSelectorPage").get_by_label("Chat").click()

    # Type in random phone number
    await page.get_by_test_id("selection-list-text-input").fill(email)

    # Click on the account name
    await page.get_by_test_id("NewChatSelectorPage").get_by_label(
        account_name, exact=True
    ).click()


async def create_expense_in_current_chat(page, amount=100):

    await page.get_by_label("Create").locator("visible=true").click()
    await page.get_by_label("Submit expense").click()
    await page.get_by_label("Manual").click()
    await page.get_by_placeholder("0").fill(str(amount))
    await page.keyboard.press("Enter")
    await page.keyboard.press("Enter")


async def wait_until_in_view(page, test_id, timeout=5000):
    # Wait until the element with the specified test ID has an `x` coordinate equal to the given value
    await page.wait_for_function(
        """(testId) => {
            const element = document.querySelector(`[data-testid="${testId}"]`);
            if (!element) return false;
            const rect = element.getBoundingClientRect();
            return rect.x + rect.width === window.innerWidth || rect.x === 0;
        }""",
        arg=[test_id],
        timeout=timeout,
    )


async def open_search_left_menu(page):
    await page.locator("button[aria-label='Search']:visible").click()


async def open_any_expense_in_view(page):
    while True:
        view_button = (
            page.locator("button[aria-label]")
            .locator("visible=true")
            .get_by_text("View")
            .first
        )
        if view_button:
            break
    await view_button.click()


async def open_chat_expense_header_top(page):
    await wait_until_in_view(page, "DisplayNamesWithTooltip")
    await page.get_by_test_id("DisplayNamesWithTooltip").get_by_text("expense").click(
        force=True
    )


async def enable_hold_in_report(page):
    await page.get_by_role("button", name="Hold").click()
    await page.get_by_role("textbox", name="Reason").fill("Hold Reason")
    await page.get_by_role("button", name="Hold expense").click()


def is_button_in_bottom_right_quarter(button_bbox, viewport):
    # Calculate the dimensions of the bottom-right quarter
    quarter_x_start = viewport["width"] / 2
    quarter_y_start = viewport["height"] / 2

    # Check if the button is contained within the bottom-right quarter
    is_contained = (
        button_bbox["x"] >= quarter_x_start
        and button_bbox["y"] >= quarter_y_start
        and button_bbox["x"] + button_bbox["width"] <= viewport["width"]
        and button_bbox["y"] + button_bbox["height"] <= viewport["height"]
    )
    return is_contained


async def verify_button_in_bottom_right_quarter(page):
    if await page.get_by_test_id("ProcessMoneyRequestHoldPage").count():
        await wait_until_in_view(page, "ProcessMoneyRequestHoldPage")
    got_it = page.get_by_role("button", name="Got it").locator("visible=true")
    await got_it.wait_for()

    viewport = page.viewport_size
    button_bbox = await got_it.bounding_box()
    is_contained = is_button_in_bottom_right_quarter(button_bbox, viewport)
    return is_contained


@pytest_asyncio.fixture
async def browser_context(config) -> AsyncGenerator[tuple[BrowserContext, Page], None]:
    """
    Provide a persistent browser with the specified platform
    """
    BROWSER_TYPE = config["BROWSER_TYPE"]
    PLATFORM = config["PLATFORM"]
    DATA_DIR = config["DATA_DIR"]

    if DATA_DIR is None:
        DATA_DIR = f"{BROWSER_TYPE}_{PLATFORM}_context"
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    # Start Playwright
    playwright = await async_playwright().start()

    context_options = {}

    if PLATFORM.lower() == "mobile":
        context_options["viewport"] = {"width": 540, "height": 864}
        context_options["is_mobile"] = True
    else:
        context_options["viewport"] = {"width": 1280, "height": 720}

    context = await playwright[BROWSER_TYPE].launch_persistent_context(
        DATA_DIR, headless=True,slow_mo=500,args=[
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                '--proxy-server=http://localhost:8080',
            ], **context_options
    )

    # persistent context already has the page
    page = context.pages[0]
    yield context, page

    # Cleanup (close the browser and stop Playwright after the test is done)
    await context.close()
    await playwright.stop()


@pytest.mark.asyncio
async def test_hold_modal_on_right_in_expense_report_search(browser_context) -> None:
    _, page = browser_context  # Unpack the page from the fixture

    await login_user_if_not_logged_in(page, "Asaad", "I")
    await start_chat(page)
    if not await page.get_by_label("View details").is_visible():
        await create_expense_in_current_chat(page, 100)
        await create_expense_in_current_chat(page, 200)
    await open_search_left_menu(page)
    await open_any_expense_in_view(page)
    if not await page.get_by_role("button", name="Got it").is_visible():
        await open_chat_expense_header_top(page)
        await enable_hold_in_report(page)
    is_contained = await verify_button_in_bottom_right_quarter(page)
    assert is_contained, "Button is not in the bottom-right quarter"
