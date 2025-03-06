import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
from playwright._impl._page import Page
from playwright.sync_api import sync_playwright

first_name = "Alice"
last_name = "Aliceoglu"


def generate_random_email():
    
    return 'testuser+1733816471@gmail.com'

def login_user(page: Page) -> None:

    username_input = page.get_by_test_id("username")
    username_input.click()

    username_input.fill(generate_random_email())

    continue_button = page.get_by_role("button", name="Continue")
    continue_button.click()
    

    join_button = page.get_by_role("button", name="Join")
    join_button.click()
    

    track_expenses_text = page.get_by_text("Track and budget expenses")
    track_expenses_text.click()

def enter_user_information(page:Page) -> None:

    first_name_input = page.get_by_role("textbox", name="First name")
    first_name_input.fill(first_name)

    first_name_input.press("Tab")

    last_name_input = page.get_by_role("textbox", name="Last name")
    last_name_input.fill(last_name)
    

    continue_button_after_names = page.get_by_role("button", name="Continue")
    continue_button_after_names.click()

def reproduce_scenario(page: Page) -> None:
    mile_rate = 100000
    

    start_chat_element  = page.get_by_label("Start chat (Floating action)")
    start_chat_element .click()

    new_workspace_element = page.get_by_text("New workspace")
    new_workspace_element .click()
    

    default_currency_element  = page.get_by_text("Default currency")
    default_currency_element .click()
    page.get_by_test_id("selection-list-text-input").fill("usd")

    currency_input_element  = page.get_by_label("USD - $")
    currency_input_element .click()


    more_features_element = page.locator('div[dir="auto"]').get_by_text("More features")
    more_features_element.click()

    add_update_enforce_element  = page.get_by_label("Add, update, and enforce")
    add_update_enforce_element .click()

    distance_rates_element  = page.get_by_test_id("WorkspaceInitialPage").get_by_text("Distance rates")
    distance_rates_element .click()

    enabled_element = page.locator('div[dir="auto"]').get_by_text("Enabled")
    enabled_element.click()
    

    rate_element = page.locator('div[dir="auto"]').get_by_text("Rate").last
    rate_element.click()
    page.get_by_placeholder("0").fill(str(mile_rate))
    
    save_element = page.get_by_role("button", name="Save")
    save_element.click()
    

    back_element = page.get_by_test_id("PolicyDistanceRateDetailsPage").get_by_label("Back")
    back_element.click()
    
    page.get_by_label("Back").first.click()
    inbox_element = page.get_by_label("Inbox")
    inbox_element.click()
    

    workspace_name = str(first_name + " " + last_name + "'s Workspace")
    collaboration_text = f"Collaboration between {first_name} {last_name} and {workspace_name} starts here!"
    collaboration_element = page.locator('div[dir="auto"]').get_by_text(collaboration_text)
    collaboration_element.click()
    

    create_button = page.get_by_role("button", name="Create")
    create_button.click()

    page.get_by_text("Track expense").click()
    page.get_by_label("Distance").click()
    

    page.get_by_test_id("IOURequestStartPage").get_by_role("button", name="Start").click()
    page.get_by_test_id("IOURequestStepWaypoint").get_by_role("textbox").fill("saray")
    page.wait_for_timeout(2000)
    page.get_by_text("Saray", exact=True).first.click()
    
    page.get_by_role("button", name="Stop").click()
    page.get_by_test_id("IOURequestStepWaypoint").get_by_role("textbox").fill("ergene")
   
    page.get_by_text("Ergene", exact=True).first.click()
   
    page.get_by_role("button", name="Next").nth(1).click()
    
    

    miles_element = page.locator('div[dir="auto"]').get_by_text("miles")
    text_content = miles_element.text_content()
    miles_value = float(text_content.split()[0])
    

    amount_element = page.locator('div[dir="auto"][data-selection-scrapper-hidden-element="false"]').get_by_text("$").first
    text_content = amount_element.text_content()
    actual_value = float(text_content.replace('$', '').replace(',', ''))


    expected_value = miles_value * mile_rate
    tolerance = 0.001
    dif = abs(actual_value - expected_value)
    assert dif < tolerance, f"Values do not match. Actual: {actual_value}, Expected: {expected_value}, Tolerance: {tolerance} Difference:{dif}"

def test_distance_amount() -> None: 
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel = "chrome",headless=True , args=["--disable-web-security",
"--disable-features=IsolateOrigins,site-per-process"
],slow_mo=2000)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        page.goto("https://127.0.0.1:8082/")
        

        login_user(page)


        enter_user_information(page)
        

        reproduce_scenario(page)

        time.sleep(1)

        context.close()
        browser.close()



