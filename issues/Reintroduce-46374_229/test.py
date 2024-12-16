import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
from playwright.sync_api import sync_playwright, expect


# Utility to generate a random email
def generate_random_email():
    postfix = int(time.time())
    # return f"testuserexpensify+{postfix}@gmail.com"
    return "testuserexpensify+1734015266@gmail.com"


def login(p, if_phone=False, first_name="John", last_name="Cena"):
    # step 1: Login
    browser = p.chromium.launch(
        channel="chrome",
        headless=True,
        args=[
            "--ignore-certificate-errors",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
        ],
        proxy={"server": "http://localhost:8080"},
        slow_mo=500,
    )

    context_args = {}
    context_args["timezone_id"] = "Asia/Karachi"
    if if_phone:
        phone = p.devices["iPhone 12 Pro"]
        context = browser.new_context(**phone, **context_args)
    else:
        context = browser.new_context(**context_args)

    page = context.new_page()

    page.goto("https://dev.new.expensify.com:8082/")

    phone_or_email_input = page.locator('input[type="email"]')
    expect(phone_or_email_input).to_be_visible()
    phone_or_email_input.fill(generate_random_email())

    time.sleep(1)

    continue_button = page.locator('button[tabindex="0"]')
    expect(continue_button).to_be_visible()
    continue_button.click()
    time.sleep(1)

    try:
        continue_button = page.locator('button[tabindex="0"]')
        expect(continue_button).to_be_visible()
        continue_button.click()
    except Exception as e:
        pass

    expect(page.locator("text=What do you want to do today?")).to_be_visible()

    try:
        # this was not available in some of the cases
        page.locator("text='Track and budget expenses'").click()
        time.sleep(1)

        # Fill the first name input field
        first_name_input = page.locator('input[name="fname"]')
        expect(first_name_input).to_be_visible()
        first_name_input.fill(first_name)
        first_name_input = page.locator('input[name="lname"]')
        expect(first_name_input).to_be_visible()
        first_name_input.fill(last_name)

        # Click on the "Continue" button using text filter
        continue_button = page.locator(
            'button[data-tag="pressable"][tabindex="0"]', has_text="Continue"
        )
        expect(continue_button).to_be_visible()
        continue_button.click()
    except:
        pass

    return browser, page


def track_expense(browser, page):
    # Click on the green plus button
    plus_icon = page.locator('button[aria-label="Start chat (Floating action)"]')
    expect(plus_icon).to_be_visible()
    plus_icon.click()

    # Click on Track Expense
    new_workspace_button = page.locator('div[aria-label="Track expense"]')
    expect(new_workspace_button).to_be_visible()
    new_workspace_button.click()
    time.sleep(1)

    # click on got it message
    got_it_button = page.locator('button:has-text("Got it")')
    expect(got_it_button).to_be_visible()
    got_it_button.click()

    # click on Manual
    manual_button = page.locator('button[aria-label="Manual"]')
    expect(manual_button).to_be_visible()
    manual_button.click()

    # Enter the amount
    page.locator('input[role="presentation"]').fill("50")

    # Click on Next button
    next_button = page.locator('button[data-listener="Enter"]', has_text="Next").first
    expect(next_button).to_be_visible()
    next_button.click()

    # click on tack expense
    track_expense_button = page.locator('button:has-text("Track expense")')
    expect(track_expense_button).to_be_visible()
    track_expense_button.click()
    time.sleep(1)

    return browser, page


def test():
    with sync_playwright() as p:
        # Step 1: Login
        browser, page = login(p, True)

        page.locator('button[aria-label="Close"]').first.click()
        # Step 2: Create expense
        browser, page = track_expense(browser, page)

        # Step 3: Go back and Click on search

        back_arrow_button = page.locator('button[aria-label="Back"]')
        expect(back_arrow_button).to_be_visible()
        back_arrow_button.click()

        search_button = page.locator('button[aria-label="Search"]')
        expect(search_button).to_be_visible()
        search_button.click()

        # Long press on the expense.
        button = page.get_by_role("button", name="John Cena")
        button.wait_for(state="visible", timeout=10000)
        button.hover()
        page.mouse.down()
        page.wait_for_timeout(1000)
        page.mouse.up()

        # click on select button
        select_button = page.locator('div[aria-label="Select"]')
        expect(select_button).to_be_visible()
        select_button.click()

        # click on 1 selected
        select_button = page.locator('button:has-text("1 selected")')
        expect(select_button).to_be_visible()
        select_button.click()

        # Click on delete
        delete_button = page.locator('div[aria-label="Delete"]')
        expect(delete_button).to_be_visible()
        delete_button.click()

        # Confirm delete
        delete_button = page.locator('button:has-text("Delete")')
        expect(delete_button).to_be_visible()
        delete_button.click()

        time.sleep(3)

        # click on select button
        b_button = page.locator('button[aria-label="Back"]')

        assert b_button.count() == 0, "Back button was not found, This is accepted."
