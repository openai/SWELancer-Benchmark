import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page



def generate_random_email():
    timestamp = int(time.time())
    return f"brianmuneneturing+{timestamp}@gmail.com"


BASE_EMAIL = "brianmuneneturing+45479@gmail.com"

def login_user(p: PlaywrightContextManager, first_name="John", last_name="Doe") -> tuple[Browser, Page, str]:

    browser = p.chromium.launch(
        channel="chromium",
        headless=True,
        args=[
            "--ignore-certificate-errors",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ],
        proxy={"server": "http://127.0.0.1:8080"},
        slow_mo=500
    )
    page = browser.new_page()


    page.goto('https://dev.new.expensify.com:8082/')


    page.locator('input[type="email"]').fill(BASE_EMAIL)
    page.locator('button[tabindex="0"]').click()
    time.sleep(1)


    try:
        page.locator('button[tabindex="0"]').click()
        time.sleep(1)
    except Exception:
        pass
    expect(page.locator("text=What do you want to do today?")).to_be_visible()



    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()
    time.sleep(1)


    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()
    time.sleep(1)

    return browser, page, first_name, last_name


def test():
    with sync_playwright() as p:

        browser, page, first_name, last_name = login_user(p)

        time.sleep(1)


        click_settings_button = page.locator("[aria-label='My settings']")
        click_settings_button.click()
        time.sleep(1)


        click_workspace_button = page.locator("div[aria-label='Workspaces']")
        click_workspace_button.click()
        time.sleep(1)


        create_new_workspace_button = page.locator(
            "[aria-label='New workspace']").nth(0)
        create_new_workspace_button.click()
        time.sleep(1)


        currency_divs = page.locator('div[aria-label*="-"]')
        currency_divs.click()
        time.sleep(1)


        click_aud_currency_button = page.locator("[aria-label='AUD - A$']")
        click_aud_currency_button.click()
        time.sleep(1)


        click_more_features = page.locator(
            "[aria-label='More features']")
        click_more_features.click()
        time.sleep(1)


        enable_distance_rates = page.locator(
            "button[aria-label='Add, update, and enforce rates.']")
        enable_distance_rates.click()
        time.sleep(1)


        click_distance_rates = page.locator(
            "div[aria-label='Distance rates']")
        click_distance_rates.click()
        time.sleep(1)


        select_existing_distance = page.locator(
            "div", has_text="Enabled").nth(-1)
        select_existing_distance.click()
        time.sleep(1)


        click_rate = page.locator(
            "div", has_text="Rate").nth(-1)
        click_rate.click()
        time.sleep(1)


        page.locator('input[type="text"]').fill("1")


        click_save = page.locator(
            "div", has_text="Save").nth(-1)
        click_save.click()
        time.sleep(1)


        click_back_button = page.locator("[aria-label='Back']").nth(-1)
        click_back_button.click()
        time.sleep(1)


        click_back_button = page.locator("[aria-label='Back']").nth(-1)
        click_back_button.click()
        time.sleep(1)



        create_new_workspace_button = page.locator(
            "[aria-label='New workspace']").nth(0)
        create_new_workspace_button.click()
        time.sleep(1)


        currency_divs = page.locator('div[aria-label*="-"]')
        currency_divs.click()
        time.sleep(1)


        click_aud_currency_button = page.locator("[aria-label='AUD - A$']")
        click_aud_currency_button.click()
        time.sleep(1)


        click_more_features = page.locator(
            "[aria-label='More features']")
        click_more_features.click()
        time.sleep(1)


        enable_distance_rates = page.locator(
            "button[aria-label='Add, update, and enforce rates.']")
        enable_distance_rates.click()
        time.sleep(1)


        click_distance_rates = page.locator(
            "div[aria-label='Distance rates']")
        click_distance_rates.click()
        time.sleep(1)


        select_existing_distance = page.locator(
            "div", has_text="Enabled").nth(-1)
        select_existing_distance.click()
        time.sleep(1)


        click_rate = page.locator(
            "div", has_text="Rate").nth(-1)
        click_rate.click()
        time.sleep(1)


        page.locator('input[type="text"]').fill("2")


        click_save = page.locator(
            "div", has_text="Save").nth(-1)
        click_save.click()
        time.sleep(1)


        click_back_button = page.locator("[aria-label='Back']").nth(-1)
        click_back_button.click()
        time.sleep(1)


        click_back_button = page.locator("[aria-label='Back']").nth(-1)
        click_back_button.click()
        time.sleep(1)


        click_start_chat = page.locator(
            '[aria-label="Start chat (Floating action)"]')
        click_start_chat.click()
        time.sleep(1)


        click_submit_expense_button = page.locator(
            "[aria-label='Submit expense']")
        click_submit_expense_button.click()
        time.sleep(1)


        click_distance = page.locator('[aria-label="Distance"]')
        click_distance.click()
        time.sleep(1)


        click_start = page.locator(
            'div[data-rbd-draggable-id="start_waypointwaypoint0"]')
        click_start.click()
        time.sleep(1)


        page.locator('input[rows="1"]').fill("est")
        time.sleep(3)


        select_first_address = page.locator('div[id="result-list-id"]').locator(
            'div', has_text="Estes Park").nth(0)
        select_first_address.click()
        time.sleep(1)


        click_stop = page.locator(
            'div[data-rbd-draggable-id="stop_waypointwaypoint1"]')
        click_stop.click()
        time.sleep(1)


        page.locator('input[rows="1"]').fill("aur")
        time.sleep(3)


        select_first_address = page.locator('div[id="result-list-id"]').locator(
            'div', has_text="Aurora").nth(0)
        select_first_address.click()
        time.sleep(5)


        click_next = page.locator(
            "div", has_text="Next").nth(-1)
        click_next.click()
        time.sleep(2)


        click_first_workspace = page.locator(
            f'button[aria-label="{first_name.capitalize()} {last_name}\'s Workspace"]')
        click_first_workspace.click()
        time.sleep(2)


        first_currency_text = page.locator(
            'div', has_text="A$").nth(-1).text_content()
        time.sleep(1)


        click_back_button = page.locator("[aria-label='Back']").nth(-1)
        click_back_button.click()
        time.sleep(1)


        click_second_workspace = page.locator(
            f'button[aria-label="{first_name.capitalize()} {last_name}\'s Workspace 1"]')
        click_second_workspace.click()
        time.sleep(1)


        second_currency_text = page.locator(
            'div', has_text="A$").nth(-1).text_content()
        time.sleep(1)


        assert first_currency_text.strip().lower() != second_currency_text.strip(
        ).lower(), "The two currency texts should not be equal."

        browser.close()

