import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import pytest
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page
from playwright.sync_api import sync_playwright, expect
from utils.trace_cleaner import trace_cleaner

NEWDOT_URL = "https://dev.new.expensify.com:8082/"
EMAIL = "turingvidhant+102@gmail.com"


def create_workspace_and_enable_feature(page: Page, feature: str):
    '''
    Creates a new workspace and enables a specified feature.

    Args:
        page (Page): The Playwright page object.
        feature (str): The feature to enable (e.g., "Invoices").
    '''
    page.locator('button[aria-label="Workspaces"]').click()

    page.get_by_test_id("WorkspaceSwitcherPage").get_by_role(
        "button", name="New workspace"
    ).click()

    page.locator('div[aria-label="More features"]').click()

    # Toggle feature
    toggle_button = page.locator(f'button[aria-label="{feature}"]')
    if not toggle_button.is_checked():
        toggle_button.click()

    page.locator('div[aria-label="Tags"]').click()


def new_dot_login(page, email):
    page.goto(NEWDOT_URL)
    page.locator('input[type="email"]').fill(email)
    page.get_by_role("button", name="Continue").nth(0).click()
    otp = '123456'
    page.locator('input[data-testid="validateCode"]').fill(otp)
    try:
        page.get_by_role("button", name="Sign In").click(timeout=2000)
    except:
        pass


def test_expensify():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=[
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
            '--proxy-server=http://localhost:8080',
        ])
        first_user_context = browser.new_context(ignore_https_errors=True)
        first_user_context.tracing.start(screenshots=True, snapshots=True, sources=True)
        page = first_user_context.new_page()

        try:
            new_dot_login(page, EMAIL)

            # Click settings
            click_settings_button = page.locator("[aria-label='My settings']")
            click_settings_button.click()

            # Click workspaces
            click_workspace_button = page.locator("div[aria-label='Workspaces']")
            click_workspace_button.click()

            # Create new workspaces
            create_new_workspace_button = page.locator(
                "[aria-label='New workspace']").nth(0)
            create_new_workspace_button.click()
            page.get_by_test_id("WorkspacePageWithSections").get_by_text("Name").click()
            workspace_elem = page.get_by_role("textbox", name="Name")

            # Extract the text (value) from the textbox
            workspace_name1 = workspace_elem.input_value()
            page.get_by_test_id("WorkspaceNamePage").get_by_label("Back").click()

            # Click Default Currency
            currency_divs = page.locator('div[aria-label*="-"]')
            currency_divs.click()

            # # Click AUD currency
            click_aud_currency_button = page.locator("[aria-label='AUD - A$']")
            click_aud_currency_button.click()

            # Click more features
            click_more_features = page.locator("[aria-label='More features']")
            click_more_features.click()

            # enable distance rates
            enable_distance_rates = page.locator(
                "button[aria-label='Add, update, and enforce rates.']")
            enable_distance_rates.click()

            # Click distance rates
            click_distance_rates = page.locator("div[aria-label='Distance rates']")
            click_distance_rates.click()

            # select existing distance rate
            select_existing_distance = page.locator("div", has_text="Enabled").nth(-1)
            select_existing_distance.click()

            # click rate
            click_rate = page.locator("div", has_text="Rate").nth(-1)
            click_rate.click()

            # input text as 1
            page.locator('input[type="text"]').fill("1")

            # click save
            click_save = page.locator("div", has_text="Save").nth(-1)
            click_save.click()

            # Click Back button
            click_back_button = page.locator("[aria-label='Back']").nth(-1)
            click_back_button.click()

            # Click Back button
            click_back_button = page.locator("[aria-label='Back']").nth(-1)
            click_back_button.click()

            # repeating the same flow of creating a workspace
            # Create new workspaces
            create_new_workspace_button = page.locator(
                "[aria-label='New workspace']").nth(0)
            create_new_workspace_button.click()
            page.get_by_test_id("WorkspacePageWithSections").get_by_text("Name").click()
            workspace_elem = page.get_by_role("textbox", name="Name")

            # Extract the text (value) from the textbox
            workspace_name2 = workspace_elem.input_value()
            page.get_by_test_id("WorkspaceNamePage").get_by_label("Back").click()

            # Click Default Currency
            currency_divs = page.locator('div[aria-label*="-"]')
            currency_divs.click()

            # # Click AUD currency
            click_aud_currency_button = page.locator("[aria-label='AUD - A$']")
            click_aud_currency_button.click()

            # Click more features
            click_more_features = page.locator("[aria-label='More features']")
            click_more_features.click()

            # enable distance rates
            enable_distance_rates = page.locator(
                "button[aria-label='Add, update, and enforce rates.']")
            enable_distance_rates.click()

            # Click distance rates
            click_distance_rates = page.locator("div[aria-label='Distance rates']")
            click_distance_rates.click()

            # select existing distance rate
            select_existing_distance = page.locator("div", has_text="Enabled").nth(-1)
            select_existing_distance.click()

            # click rate
            click_rate = page.locator("div", has_text="Rate").nth(-1)
            click_rate.click()

            # input text as 1
            page.locator('input[type="text"]').fill("2")

            # click save
            click_save = page.locator("div", has_text="Save").nth(-1)
            click_save.click()

            # Click Back button
            click_back_button = page.locator("[aria-label='Back']").nth(-1)
            click_back_button.click()

            # Click Back button
            click_back_button = page.locator("[aria-label='Back']").nth(-1)
            click_back_button.click()

            # Click Inbox button
            click_start_chat = page.locator('[aria-label="Start chat (Floating action)"]')
            click_start_chat.click()

            # Click submit expense
            click_submit_expense_button = page.locator("[aria-label='Submit expense']")
            click_submit_expense_button.click()

            # Click Distance
            click_distance = page.locator('[aria-label="Distance"]')
            click_distance.click()

            # Click start
            click_start = page.locator('div[data-rbd-draggable-id="start_waypointwaypoint0"]')
            click_start.click()

            # fill the start address
            page.locator('input[rows="1"]').fill("est")

            # select the address from the dropdown
            select_first_address = page.locator('div[id="result-list-id"]').locator(
                'div', has_text="Estes Park").nth(0)
            select_first_address.click()

            click_stop = page.locator('div[data-rbd-draggable-id="stop_waypointwaypoint1"]')
            click_stop.click()

            # fill the stop address
            page.locator('input[rows="1"]').fill("aur")

            # select the address from the dropdown
            select_first_address = page.locator('div[id="result-list-id"]').locator(
                'div', has_text="Aurora").nth(0)
            select_first_address.click()

            # click Next
            click_next = page.locator("div", has_text="Next").nth(-1)
            click_next.click()

            # Select first workspace
            click_first_workspace = page.get_by_label(workspace_name1)
            click_first_workspace.click()

            # Locate the div that contains the A$ symbol
            first_currency_text = page.locator('div', has_text="A$").nth(-1).text_content()

            # Click Back button
            click_back_button = page.locator("[aria-label='Back']").nth(-1)
            click_back_button.click()

            # Select first workspace
            click_second_workspace = page.get_by_label(workspace_name2)
            click_second_workspace.click()

            # Locate the div that contains the A$ symbol
            second_currency_text = page.locator('div', has_text="A$").nth(-1).text_content()

            # Assert that the two text values are not equal
            assert first_currency_text.strip().lower() != second_currency_text.strip().lower(), "The two currency texts should not be equal."

        except Exception as e:
            raise e
        finally:
            first_user_context.tracing.stop(path='/app/expensify/user_tool/output_browser1.zip')
            trace_cleaner('/app/expensify/user_tool/output_browser1.zip')
            page.close()
            browser.close()
