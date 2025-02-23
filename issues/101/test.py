import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import pytest
from playwright.async_api import TimeoutError, expect, async_playwright
from playwright._impl._page import Page
from utils.login import sign_up, complete_onboarding
from utils.browser import close_browser
from utils.email_handler import get_specific_derived_email

BASE_EMAIL = 'testuserexpensify@gmail.com'
PROXY_SERVER = 'http://127.0.0.1:8080'


async def start_mobile_browser_with_proxy(playwright):
    mobile_context = {
        'viewport': {'width': 540, 'height': 864},
        'is_mobile': True,
    }

    browser = await playwright.chromium.launch(
        slow_mo=700,
        headless=True,
        proxy={
            'server': PROXY_SERVER
        },
        args=[
            '--ignore-certificate-errors',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process'
        ]
    )
    context = await browser.new_context(
        ignore_https_errors=True,
        viewport=mobile_context['viewport'],  # Apply mobile viewport
        is_mobile=mobile_context['is_mobile']  # Set mobile flag
    )
    page = await context.new_page()
    return context, page


async def create_account(page: Page, email: str, first_name: str, last_name: str):

    await sign_up(page, email)


    try:
        await complete_onboarding(page, first_name=first_name, last_name=last_name)
    except Exception:
        pass

    await page.wait_for_timeout(2000)
    if await page.locator('button:has-text("Get started")').is_visible():
        await page.locator('button:has-text("Get started")').click()
    if await page.get_by_text('Get started here').is_visible():
        await page.mouse.click(0,0)


    await expect(page.get_by_label("Inbox")).to_be_visible()


async def send_message_to_user(page: Page, email: str, message: str):

    await page.locator('button[aria-label="Start chat (Floating action)"]').click()
    await page.locator('div[aria-label="Start chat"][role="menuitem"]').click()


    await page.locator('input[aria-label="Name, email, or phone number"]').fill(email)
    await page.wait_for_timeout(1000)
    await page.get_by_test_id('selection-list').locator(f'button:has-text("{email}")').click()
    await page.wait_for_timeout(1000)


    message_editor = page.locator('div[contenteditable="true"][placeholder="Write something..."]').last
    await message_editor.fill(message)
    await message_editor.press("Enter")


async def verify_emoji_preview_alignment(page: Page, username: str, email: str, message: str):

    message_preview = page.get_by_label("Last chat message preview").filter(has_text=message)
    await message_preview.wait_for()


    parent_element = message_preview.locator("..")
    parent_box = await parent_element.bounding_box()


    children_elements = await parent_element.locator("> *").element_handles()

    height_of_children = 0
    width_of_children = 0

    for child in children_elements:
        child_box = await child.bounding_box()
        if child_box['width'] == parent_box['width']:

            height_of_children += child_box['height']
        else:

            width_of_children += child_box['width']

    await page.wait_for_timeout(1000)


    if height_of_children > 0:
        assert height_of_children == parent_box['height'], "The message preview is not vertically aligned."
    if width_of_children > 0:
        assert width_of_children == parent_box['width'], "The message preview is not horizontally aligned."


@pytest.mark.asyncio
async def test_chat_emoji_preview_alignment_mobile():
    """
    Test that the chat emoji preview is shown correctly on mobile
    """
    try:

        playwright = await async_playwright().start()


        context2, page2 = await start_mobile_browser_with_proxy(playwright)
        context1, page1 = await start_mobile_browser_with_proxy(playwright)


        user1_email = get_specific_derived_email(BASE_EMAIL, '76178929')
        user2_email = get_specific_derived_email(BASE_EMAIL, '76829729')
        await create_account(page1, user1_email, 'John', 'Doe')
        await page2.bring_to_front()
        await create_account(page2, user2_email, 'Jane', 'Doe')

        message_with_emoji = "Hello 🏫"


        await send_message_to_user(page2, user1_email, message_with_emoji)
        await page1.bring_to_front()
        await page1.wait_for_timeout(5000)

        await verify_emoji_preview_alignment(page1, 'John Doe', user1_email, message_with_emoji)
    finally:

        await context1.close()
        await context2.close()
        await playwright.stop()
