import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import re

from playwright.sync_api import Page, sync_playwright
from playwright.async_api import expect
from playwright.sync_api._context_manager import Playwright
from utils.trace_cleaner import trace_cleaner


def generate_random_email():
    return f"expensifyapp97+9034138199@gmail.com"


def create_user(p: Playwright, firstname: str, lastname: str):


    phone = p.devices["Galaxy S8"]
    proxy = {"server": "http://127.0.0.1:8080/"}
    args = ["--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"]
    browser = p.chromium.launch(headless=True, proxy=proxy, args=args)
    context = browser.new_context(**phone)
    page = context.new_page()


    page.goto("https://dev.new.expensify.com:8082/")


    user_email = generate_random_email()
    page.get_by_test_id("username").fill(
        user_email
    )
    page.wait_for_timeout(1000)
    page.get_by_role("button", name="Continue").click()
    page.wait_for_timeout(1000)
    page.get_by_role("button", name="Join").click()
    page.wait_for_timeout(1000)


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
        context = page.context
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        try:
            close_button_if_present(page)
            print("Name = ", is_name)


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


            page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()
            page.get_by_label("New workspace").first.click()


            page.get_by_label("Back").last.click()
            page.get_by_label("Back").last.click()


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


            element_handle = merchant_details.element_handle()
            text_overflow = element_handle.evaluate(
                "el => window.getComputedStyle(el).textOverflow"
            )
            assert (
                text_overflow != "ellipsis"
            ), f"Text is truncated due to text-overflow: {text_overflow}"
        except Exception as e:
            print(f"Test encountered an exception: {e}")
            raise e
        finally:
            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            browser.close()
