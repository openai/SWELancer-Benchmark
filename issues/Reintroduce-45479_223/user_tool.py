import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page
from utils.trace_cleaner import trace_cleaner  # <--- Added import


# Utility to generate a random email
def generate_random_email():
    return f"test+19099@gmail.com"


def login_user(p: PlaywrightContextManager, first_name="John", last_name="Doe") -> tuple[Browser, Page, str]:
    # Launch chromiun and open new page
    proxy = {"server": "http://127.0.0.1:8080/"}
    args = ["--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"]
    browser = p.chromium.launch(headless=True, proxy=proxy, args=args, slow_mo=500)
    page = browser.new_page()
    user_email = generate_random_email()

    # Step 1: Open expensify url
    page.goto('https://dev.new.expensify.com:8082/')

    # Step 2: Enter email and click continue
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()
    time.sleep(1)

    # Step 3: Click join button
    try:
        page.locator('button[tabindex="0"]').click()
        time.sleep(1)
    except Exception:
        pass
    expect(page.locator("text=What do you want to do today?")).to_be_visible()

    # Step 4: Select 'Track and budget expenses' in onobarding page and click Continue

    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()
    time.sleep(1)

    # Step 5: Enter first name, last name and click continue
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()
    time.sleep(1)

    return browser, page, first_name, last_name


def test():
    with sync_playwright() as p:
        browser = None
        context = None
        try:
            # Step 1: Login user
            browser, page, first_name, last_name = login_user(p)
            context = page.context
            # Start tracing
            context.tracing.start(screenshots=True, snapshots=True, sources=True)

            time.sleep(1)

            # Click settings
            click_settings_button = page.locator("[aria-label='My settings']")
            click_settings_button.click()
            time.sleep(1)

            # Click workspaces
            click_workspace_button = page.locator("div[aria-label='Workspaces']")
            click_workspace_button.click()
            time.sleep(1)

            # Create new workspaces
            create_new_workspace_button = page.locator(
                "[aria-label='New workspace']").nth(0)
            create_new_workspace_button.click()
            time.sleep(1)

            # Click Default Currency
            currency_divs = page.locator('div[aria-label*="-"]')
            currency_divs.click()
            time.sleep(1)

            # # Click AUD currency
            click_aud_currency_button = page.locator("[aria-label='AUD - A$']")
            click_aud_currency_button.click()
            time.sleep(1)

            # Click more features
            click_more_features = page.locator(
                "[aria-label='More features']")
            click_more_features.click()
            time.sleep(1)

            # enable distance rates
            enable_distance_rates = page.locator(
                "button[aria-label='Add, update, and enforce rates.']")
            enable_distance_rates.click()
            time.sleep(1)

            # Click distance rates
            click_distance_rates = page.locator(
                "div[aria-label='Distance rates']")
            click_distance_rates.click()
            time.sleep(1)

            # select existing distance rate
            select_existing_distance = page.locator(
                "div", has_text="Enabled").nth(-1)
            select_existing_distance.click()
            time.sleep(1)

            # click rate
            click_rate = page.locator(
                "div", has_text="Rate").nth(-1)
            click_rate.click()
            time.sleep(1)

            # input text as 1
            page.locator('input[type="text"]').fill("1")

            # click save
            click_save = page.locator(
                "div", has_text="Save").nth(-1)
            click_save.click()
            time.sleep(1)

            # Click Back button
            click_back_button = page.locator("[aria-label='Back']").nth(-1)
            click_back_button.click()
            time.sleep(1)

            # Click Back button
            click_back_button = page.locator("[aria-label='Back']").nth(-1)
            click_back_button.click()
            time.sleep(1)

            # repeating the same flow of creating a workspace
            # Create new workspaces
            create_new_workspace_button = page.locator(
                "[aria-label='New workspace']").nth(0)
            create_new_workspace_button.click()
            time.sleep(1)

            # Click Default Currency
            currency_divs = page.locator('div[aria-label*="-"]')
            currency_divs.click()
            time.sleep(1)

            # # Click AUD currency
            click_aud_currency_button = page.locator("[aria-label='AUD - A$']")
            click_aud_currency_button.click()
            time.sleep(1)

            # Click more features
            click_more_features = page.locator(
                "[aria-label='More features']")
            click_more_features.click()
            time.sleep(1)

            # enable distance rates
            enable_distance_rates = page.locator(
                "button[aria-label='Add, update, and enforce rates.']")
            enable_distance_rates.click()
            time.sleep(1)

            # Click distance rates
            click_distance_rates = page.locator(
                "div[aria-label='Distance rates']")
            click_distance_rates.click()
            time.sleep(1)

            # select existing distance rate
            select_existing_distance = page.locator(
                "div", has_text="Enabled").nth(-1)
            select_existing_distance.click()
            time.sleep(1)

            # click rate
            click_rate = page.locator(
                "div", has_text="Rate").nth(-1)
            click_rate.click()
            time.sleep(1)

            # input text as 1
            page.locator('input[type="text"]').fill("2")

            # click save
            click_save = page.locator(
                "div", has_text="Save").nth(-1)
            click_save.click()
            time.sleep(1)

            # Click Back button
            click_back_button = page.locator("[aria-label='Back']").nth(-1)
            click_back_button.click()
            time.sleep(1)

            # Click Back button
            click_back_button = page.locator("[aria-label='Back']").nth(-1)
            click_back_button.click()
            time.sleep(1)

            # Click Inbox button
            click_start_chat = page.locator(
                '[aria-label="Start chat (Floating action)"]')
            click_start_chat.click()
            time.sleep(1)

            # Click submit expense
            click_submit_expense_button = page.locator(
                "[aria-label='Submit expense']")
            click_submit_expense_button.click()
            time.sleep(1)

            # Click Distance
            click_distance = page.locator('[aria-label="Distance"]')
            click_distance.click()
            time.sleep(1)

            # Click start
            click_start = page.locator(
                'div[data-rbd-draggable-id="start_waypointwaypoint0"]')
            click_start.click()
            time.sleep(1)

            # fill the start address
            page.locator('input[rows="1"]').fill("est")
            time.sleep(3)

            # select the address from the dropdown
            select_first_address = page.locator('div[id="result-list-id"]').locator(
                'div', has_text="Estes Park").nth(0)
            select_first_address.click()
            time.sleep(1)

            # Click stop
            click_stop = page.locator(
                'div[data-rbd-draggable-id="stop_waypointwaypoint1"]')
            click_stop.click()
            time.sleep(1)

            # fill the stop address
            page.locator('input[rows="1"]').fill("aur")
            time.sleep(3)

            # select the address from the dropdown
            select_first_address = page.locator('div[id="result-list-id"]').locator(
                'div', has_text="Aurora").nth(0)
            select_first_address.click()
            time.sleep(5)

            # click Next
            click_next = page.locator(
                "div", has_text="Next").nth(-1)
            click_next.click()
            time.sleep(2)

            # Select first workspace
            click_first_workspace = page.locator(
                f'button[aria-label="{first_name.capitalize()} {last_name}\\'s Workspace"]')
            click_first_workspace.click()
            time.sleep(2)

            # Locate the div that contains the A$ symbol
            first_currency_text = page.locator(
                'div', has_text="A$").nth(-1).text_content()
            time.sleep(1)

            # Click Back button
            click_back_button = page.locator("[aria-label='Back']").nth(-1)
            click_back_button.click()
            time.sleep(1)

            # Select first workspace
            click_second_workspace = page.locator(
                f'button[aria-label="{first_name.capitalize()} {last_name}\\'s Workspace 1"]')
            click_second_workspace.click()
            time.sleep(1)

            # Locate the div that contains the A$ symbol
            second_currency_text = page.locator(
                'div', has_text="A$").nth(-1).text_content()
            time.sleep(1)

            # Assert that the two text values are not equal
            assert first_currency_text.strip().lower() != second_currency_text.strip().lower(), "The two currency texts should not be equal."

        except Exception as e:
            raise e
        finally:
            if context:
                # Stop tracing and save
                context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
                # Clean trace
                trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            if browser:
                browser.close()
