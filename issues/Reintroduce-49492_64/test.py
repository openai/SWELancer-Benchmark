import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import pytest
from playwright.async_api import async_playwright, expect
import pytest_asyncio


async def login_user(p, first_name="Milan", last_name="T"):
    # Launch chromium and open a new page
    browser = await p.chromium.launch(headless=True,slow_mo=500, args=[
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                '--proxy-server=http://localhost:8080',
            ])
    page = await browser.new_page()
    user_email =f"expensify31+10052@gmail.com"

    # Step 1: Open Expensify URL
    await page.goto('https://dev.new.expensify.com:8082/')

    # Step 2: Enter email and click continue
    await page.locator('input[type="email"]').fill(user_email)
    await page.locator('button[tabindex="0"]').click()
    await page.wait_for_timeout(2000)

    # Step 3: Click join button
    try:
        await page.locator('button[tabindex="0"]').click()
        await page.wait_for_timeout(1000)
    except Exception:
        pass

    # Step 4: Select 'Track and budget expenses' in onboarding page and click Continue
    await page.locator("text='Track and budget expenses'").click()
    await page.get_by_role("button", name="Continue").click()
    await page.wait_for_timeout(1000)

    # Step 5: Enter first name, last name and click continue
    await page.locator('input[name="fname"]').fill(first_name)
    await page.locator('input[name="lname"]').fill(last_name)
    await page.get_by_role("button", name="Continue").last.click()
    await page.wait_for_timeout(1000)

    return browser, page, user_email

async def submit_expense_in_workspace_chat(browser, page, user_email, amount="1000"):
    # Step 1: Click on workspace chat
    workspace_chat = page.locator('button[aria-label="Navigates to a chat"]', has_text="Milan T's Workspace")
    await workspace_chat.click()
    await page.wait_for_timeout(1000)

    # Step 2: Click on "+" icon and click submit expense
    plus_create_icon = page.locator('button[aria-label="Create"]').last
    await plus_create_icon.click()
    await page.wait_for_timeout(1000)

    submit_expense_button = page.locator('div[aria-label="Submit expense"]')
    await submit_expense_button.click()
    await page.wait_for_timeout(1000)

    # Step 3: Click on "Manual" button and enter amount
    manual_button = page.locator('button[aria-label="Manual"]')
    await manual_button.click()
    await page.wait_for_timeout(1000)

    await page.locator('input[role="presentation"]').fill(amount)

    # Step 4: Click on Next button
    next_button = page.locator('button[data-listener="Enter"]', has_text="Next").first
    await next_button.click()
    await page.wait_for_timeout(1000)

    # Step 5: Add merchant details
    merchant_field = page.locator('div[role="menuitem"]', has_text="Merchant")
    await merchant_field.click()
    await page.wait_for_timeout(1000)

    await page.locator('input[aria-label="Merchant"]').fill("Test Merchant")

    save_button = page.locator('button', has_text="Save")
    await save_button.click()
    await page.wait_for_timeout(1000)

    # Step 6: Submit the expense
    save_button = page.locator('button[data-listener="Enter"]', has_text="Submit")
    await save_button.click()
    await page.wait_for_timeout(1000)

    return browser, page, user_email

@pytest_asyncio.fixture
async def setup():
    async with async_playwright() as p:
        browser, page, user_email = await login_user(p)
        yield browser, page, user_email
        await browser.close()

@pytest.mark.asyncio
async def test_delete_saved_search(setup):
    browser, page, user_email = setup

    # Step 2: Click on + icon and click on "New workspace"
    plus_icon = page.locator('button[aria-label="Start chat (Floating action)"]')
    await plus_icon.click()
    await page.wait_for_timeout(2000)

    new_workspace_button = page.locator('div[aria-label="New workspace"]')
    await new_workspace_button.click()
    await page.wait_for_timeout(1000)

    # Step 3: Click on Back arrow to go back and navigate to inbox screen
    back_arrow_button = page.locator('button[aria-label="Back"]')
    await back_arrow_button.click()

    inbox_menu = page.locator('button[aria-label="Inbox"]')
    await inbox_menu.click()
    await page.wait_for_timeout(2000)

    # Step 4: Submit an expense
    await submit_expense_in_workspace_chat(browser, page, user_email)

    await submit_expense_in_workspace_chat(browser, page, user_email)

    await page.locator('button[aria-label="Search"]').click()
    await page.wait_for_timeout(3000)

    await page.get_by_role("button", name="Filters").click()
    await page.locator("div:nth-child(2) > div > div > div > div > div > div > div > div > div:nth-child(2) > div > div > div:nth-child(7) > div > div > div > div > div > div > div > .css-view-175oi2r").first.click()
    await page.get_by_role("textbox", name="Keyword").fill("Model")
    await page.get_by_role("button", name="Save").click()
    await page.get_by_role("button", name="Save search").click()
    await page.get_by_label("More").click()

    await page.wait_for_timeout(1000)
    await page.locator('div[aria-label="Delete"][role="menuitem"]').click()

    await page.press("body", "Enter")

    element = page.locator('button:has-text("Delete")')
    await expect(element).not_to_be_visible()

    await browser.close()

