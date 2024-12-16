import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import re

from playwright.sync_api import Page, sync_playwright
from playwright.async_api import expect
from playwright.sync_api._context_manager import Playwright


# Utility to generate a random email
def generate_random_email():
    return f"expensifyapp97+9034138199@gmail.com"


def create_user(p: Playwright, firstname: str, lastname: str):
    
    # Launch chromium and open new page
    phone = p.devices["Galaxy S8"]
    proxy = {"server": "http://127.0.0.1:8080/"}
    args = ["--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"]
    browser = p.chromium.launch(headless=True, proxy=proxy, args=args)
    context = browser.new_context(**phone)
    page = context.new_page()

    # create user
    page.goto("https://dev.new.expensify.com:8082/")
    
    # Sign up
    user_email = generate_random_email()
    page.get_by_test_id("username").fill(
        user_email
    )
    page.wait_for_timeout(1000)
    page.get_by_role("button", name="Continue").click()
    page.wait_for_timeout(1000)
    page.get_by_role("button", name="Join").click()
    page.wait_for_timeout(1000)

    # Update profile
    is_name_set = True
    try:
        page.get_by_text("Track and budget expenses").click()
        page.get_by_role("textbox", name="First name").fill(firstname)
        page.get_by_role("textbox", name="Last name").fill(lastname)
        page.wait_for_timeout(1000)
        page.get_by_role("button", name="Continue").click()
        page.wait_for_timeout(1000)
    except Exception:
        is_name_set = False
    
    return page, browser, user_email, is_name_set

def close_button_if_present(page: Page):
    """
    Occasionally, there is a close button that prevents any clicks on the page as
    it covers most of the screen. This button cannot be seen visually.
    """
    close_button = page.locator('button[aria-label="Close"]')
    if close_button.is_visible():
        close_button.click()


def test_merchant_details():

    with sync_playwright() as p:
        
        first_name = 'Milan'
        last_name = 'T'

        page, browser, user_email, is_name = create_user(p, first_name, last_name)
        close_button_if_present(page)
        print("Name = ", is_name)
        
        # set first name and last name
        if not is_name:
            page.get_by_label("My settings").click()
            page.get_by_label("Profile").last.click()
            page.get_by_label(user_email).first.click()
            page.get_by_role("textbox", name="First name").click()
            page.get_by_role("textbox", name="First name").fill(first_name)
            page.get_by_role("textbox", name="Last name").click()
            page.get_by_role("textbox", name="Last name").fill(last_name)
            page.get_by_role("button", name="Save").click()
            page.get_by_label("Back").first.click()

        # Enable workspace
        page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()
        page.get_by_label("New workspace").first.click()

        # Go back home
        page.get_by_label("Back").last.click()
        page.get_by_label("Back").last.click()

        # Submit an expense to workspace
        page.get_by_label("Start chat (Floating action)").click()
        page.get_by_label("Submit expense").first.click()
        page.get_by_label("Manual").click()
        page.get_by_placeholder("0").fill("10")
        currency = page.get_by_label("Select a currency").inner_text()
        currency = len(currency) == 1 and currency or f"{currency} "
        page.locator("#numPadContainerView").get_by_role("button", name="Next").click()
        page.get_by_label(f"{first_name} {last_name}'s Workspace").click()
        page.get_by_role("menuitem", name="Merchant Required").click()

        long_merchant_details = (
            "https://staging.new.expensify.com/r/575354256634947/165034783536884819"
        )
        page.get_by_role("textbox", name="Merchant").fill(long_merchant_details)
        page.get_by_role("button", name="Save").click()
        page.get_by_role("button", name=f"Submit {currency}").click()
        page.get_by_role("button", name=re.compile(r"Pay .* elsewhere")).click()
        page.get_by_label("View details").click()

        merchant_details = page.locator(
            f'div[data-selection-scrapper-hidden-element="false"]:has-text("{long_merchant_details}")'
        )

        # Assert that the text is not visually truncated
        element_handle = merchant_details.element_handle()
        text_overflow = element_handle.evaluate(
            "el => window.getComputedStyle(el).textOverflow"
        )
        assert (
            text_overflow != "ellipsis"
        ), f"Text is truncated due to text-overflow: {text_overflow}"

        # ---------------------
        browser.close()