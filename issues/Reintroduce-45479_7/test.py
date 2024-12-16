import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page


# Utility to generate a random email
def generate_random_email():
    timestamp = int(time.time())
    return f"aliceoglualice+{1734466074}@gmail.com"


def login_user(p: PlaywrightContextManager, first_name="John", last_name="Doe") -> tuple[Browser, Page, str]:
    # Launch chromiun and open new page
    browser = p.chromium.launch(headless=True, args=["--ignore-certificate-errors",
                                                        "--disable-web-security",
                                                        "--disable-features=IsolateOrigins,site-per-process"], 
                                                        slow_mo=500)
    page = browser.new_page()
    user_email = generate_random_email()

    # Step 1: Open expensify url
    page.goto('https://dev.new.expensify.com:8082/')

    # Step 2: Enter email and click continue
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(1000)

    # Step 3: Click join button
    try:
        page.locator('button[tabindex="0"]').click()
        page.wait_for_timeout(1000)
    except Exception:
        pass
    expect(page.locator("text=What do you want to do today?")).to_be_visible()

    # Step 4: Select 'Track and budget expenses' in onobarding page and click Continue

    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()
    page.wait_for_timeout(1000)

    # Step 5: Enter first name, last name and click continue
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()
    page.wait_for_timeout(1000)

    return browser, page, first_name, last_name


def test():
    with sync_playwright() as p:
        # Step 1: Login user
        browser, page, first_name, last_name = login_user(p)

        page.wait_for_timeout(1000)

        # Click settings
        click_settings_button = page.locator("[aria-label='My settings']")
        click_settings_button.click()
        page.wait_for_timeout(1000)

        # Click workspaces
        click_workspace_button = page.locator("div[aria-label='Workspaces']")
        click_workspace_button.click()
        page.wait_for_timeout(1000)

        # Create new workspaces
        create_new_workspace_button = page.locator("[aria-label='New workspace']").nth(0)
        create_new_workspace_button.click()
        page.wait_for_timeout(1000)

        # Click Default Currency
        currency_divs = page.locator('div[aria-label*="-"]')
        currency_divs.click()
        page.wait_for_timeout(1000)

        # # Click AUD currency
        click_aud_currency_button = page.locator("[aria-label='AUD - A$']")
        click_aud_currency_button.click()
        page.wait_for_timeout(1000)

        # Click more features
        click_more_features = page.locator("[aria-label='More features']")
        click_more_features.click()
        page.wait_for_timeout(1000)

        # enable distance rates
        enable_distance_rates = page.locator("button[aria-label='Add, update, and enforce rates.']")
        enable_distance_rates.click()
        page.wait_for_timeout(1000)

        # Click distance rates
        click_distance_rates = page.locator("div[aria-label='Distance rates']")
        click_distance_rates.click()
        page.wait_for_timeout(1000)

        # select existing distance rate
        select_existing_distance = page.locator("div", has_text="Enabled").nth(-1)
        select_existing_distance.click()
        page.wait_for_timeout(1000)

        # click rate
        click_rate = page.locator("div", has_text="Rate").nth(-1)
        click_rate.click()
        page.wait_for_timeout(1000)

        # input text as 1
        page.locator('input[type="text"]').fill("1")

        # click save
        click_save = page.locator("div", has_text="Save").nth(-1)
        click_save.click()
        page.wait_for_timeout(1000)

        # Click Back button
        click_back_button = page.locator("[aria-label='Back']").nth(-1)
        click_back_button.click()
        page.wait_for_timeout(1000)

        # Click Back button
        click_back_button = page.locator("[aria-label='Back']").nth(-1)
        click_back_button.click()
        page.wait_for_timeout(1000)

        # repeating the same flow of creating a workspace
        # Create new workspaces
        create_new_workspace_button = page.locator("[aria-label='New workspace']").nth(0)
        create_new_workspace_button.click()
        page.wait_for_timeout(1000)

        # Click Default Currency
        currency_divs = page.locator('div[aria-label*="-"]')
        currency_divs.click()
        page.wait_for_timeout(1000)

        # # Click AUD currency
        click_aud_currency_button = page.locator("[aria-label='AUD - A$']")
        click_aud_currency_button.click()
        page.wait_for_timeout(1000)

        # Click more features
        click_more_features = page.locator("[aria-label='More features']")
        click_more_features.click()
        page.wait_for_timeout(1000)

        # enable distance rates
        enable_distance_rates = page.locator("button[aria-label='Add, update, and enforce rates.']")
        enable_distance_rates.click()
        page.wait_for_timeout(1000)

        # Click distance rates
        click_distance_rates = page.locator("div[aria-label='Distance rates']")
        click_distance_rates.click()
        page.wait_for_timeout(1000)

        # select existing distance rate
        select_existing_distance = page.locator("div", has_text="Enabled").nth(-1)
        select_existing_distance.click()
        page.wait_for_timeout(1000)

        # click rate
        click_rate = page.locator("div", has_text="Rate").nth(-1)
        click_rate.click()
        page.wait_for_timeout(1000)

        # input text as 1
        page.locator('input[type="text"]').fill("2")

        # click save
        click_save = page.locator("div", has_text="Save").nth(-1)
        click_save.click()
        page.wait_for_timeout(1000)

        # Click Back button
        click_back_button = page.locator("[aria-label='Back']").nth(-1)
        click_back_button.click()
        page.wait_for_timeout(1000)

        # Click Back button
        click_back_button = page.locator("[aria-label='Back']").nth(-1)
        click_back_button.click()
        page.wait_for_timeout(1000)

        # Click Inbox button
        click_start_chat = page.locator('[aria-label="Start chat (Floating action)"]')
        click_start_chat.click()
        page.wait_for_timeout(1000)

        # Click submit expense
        click_submit_expense_button = page.locator("[aria-label='Submit expense']")
        click_submit_expense_button.click()
        page.wait_for_timeout(1000)

        # Click Distance
        click_distance = page.locator('[aria-label="Distance"]')
        click_distance.click()
        page.wait_for_timeout(1000)

        # Click start
        click_start = page.locator('div[data-rbd-draggable-id="start_waypointwaypoint0"]')
        click_start.click()
        page.wait_for_timeout(1000)

        # fill the start address
        page.locator('input[rows="1"]').fill("est")
        page.wait_for_timeout(3000)

        # select the address from the dropdown
        select_first_address = page.locator('div[id="result-list-id"]').locator('div', has_text="Estes Park").nth(0)
        select_first_address.click()
        page.wait_for_timeout(1000)

        # Click stop
        click_stop = page.locator('div[data-rbd-draggable-id="stop_waypointwaypoint1"]')
        click_stop.click()
        page.wait_for_timeout(1000)

        # fill the stop address
        page.locator('input[rows="1"]').fill("aur")
        page.wait_for_timeout(3000)

        # select the address from the dropdown
        select_first_address = page.locator('div[id="result-list-id"]').locator('div', has_text="Aurora").nth(0)
        select_first_address.click()
        page.wait_for_timeout(5000)

        # click Next
        click_next = page.locator("div", has_text="Next").nth(-1)
        click_next.click()
        page.wait_for_timeout(2000)

        # Select first workspace
        click_first_workspace = page.locator(f'button[aria-label="{first_name.capitalize()} {last_name}\'s Workspace"]')
        click_first_workspace.click()
        page.wait_for_timeout(2000)

        # Locate the div that contains the A$ symbol
        first_currency_text = page.locator('div', has_text="A$").nth(-1).text_content()
        page.wait_for_timeout(1000)

        # Click Back button
        click_back_button = page.locator("[aria-label='Back']").nth(-1)
        click_back_button.click()
        page.wait_for_timeout(1000)

        # Select first workspace
        click_second_workspace = page.locator(f'button[aria-label="{first_name.capitalize()} {last_name}\'s Workspace 1"]')
        click_second_workspace.click()
        page.wait_for_timeout(1000)

        # Locate the div that contains the A$ symbol
        second_currency_text = page.locator('div', has_text="A$").nth(-1).text_content()
        page.wait_for_timeout(1000)

        # Assert that the two text values are not equal
        assert first_currency_text.strip().lower() != second_currency_text.strip().lower(), "The two currency texts should not be equal."

        browser.close()


