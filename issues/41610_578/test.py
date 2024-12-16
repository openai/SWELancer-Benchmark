import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from time import time
from playwright.sync_api import sync_playwright, expect
from playwright._impl._page import Page


def generate_random_email():
    timestamp = int(time())
    # return f"bobexpensifytest+{timestamp}@gmail.com"
    return "bobexpensifytest+1733402509@gmail.com"


def login_user(page: Page, user_email: str, first_name="Milan", last_name="T") -> Page:
    # Step 1: Open expensify url
    page.goto("https://dev.new.expensify.com:8082/")

    # Step 2: Enter email and click continue
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(1000)

    # Step 3: Click join button
    try:
        page.locator('button[tabindex="0"]').click()
    except Exception:
        pass
    expect(page.locator("text=What do you want to do today?")).to_be_visible()

    # Step 4: Select 'Track and budget expenses' in onobarding page and click Continue
    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()

    # Step 5: Enter first name, last name and click continue
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()

    return page


def launch_app(p, headless=True, device=None, geolocation=None):
    """
    Launch the Expensify app.
    """
    browser = p.chromium.launch(
        channel="chrome",
        headless=True,
        args=[
            "--ignore-certificate-errors",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
        ],
        proxy={"server": "http://localhost:8080"},
        slow_mo=1000,
    )
    context_args = {}
    if device:
        context_args.update(p.devices[device])
    if geolocation:
        context_args["geolocation"] = geolocation
        context_args["permissions"] = ["geolocation"]

    context_args["timezone_id"] = "Asia/Karachi"
    context = browser.new_context(**context_args)
    page = context.new_page()
    return browser, context, page


def test_mobile_get_assistance_page():
    with sync_playwright() as p:
        browser, context, page = launch_app(p, device="iPhone 12 Pro")

        user_email = generate_random_email()

        # Step 1: Login as Bob
        page = login_user(page, user_email, first_name="Bob")

        try:
            page.locator('button[aria-label="Close"]').click(timeout=3000)
        except Exception:
            print("Did not find close!")
            pass

        plus_icon = page.locator('button[aria-label="Start chat (Floating action)"]')
        expect(plus_icon).to_be_visible()
        plus_icon.click()

        new_workspace_button = page.locator('div[aria-label="New workspace"]')
        expect(new_workspace_button).to_be_visible()
        new_workspace_button.click()

        more_features_button = page.locator(
            'div[aria-label="More features"][role="menuitem"]'
        )
        expect(more_features_button).to_be_visible()
        more_features_button.click()

        workflow_switch = page.locator(
            'button[aria-label="Configure how spend is approved and paid."][role="switch"]'
        )
        expect(workflow_switch).to_be_visible()
        workflow_switch.click()

        workflows_button = page.locator('div[aria-label="Workflows"][role="menuitem"]')
        expect(workflows_button).to_be_visible()
        workflows_button.click()

        connect_bank_account = page.locator(
            'div[aria-label="Connect bank account"][role="menuitem"]'
        )
        expect(connect_bank_account).to_be_visible()
        connect_bank_account.click()

        update_to_usd = page.locator(
            'button[data-listener="Enter"]', has_text="Update to USD"
        )
        expect(update_to_usd).to_be_visible()
        update_to_usd.click()

        page.wait_for_timeout(2000)

        get_assistant = page.locator(
            'button[aria-label="Get assistance from our team"][role="button"]'
        )
        expect(get_assistant).to_be_visible()
        get_assistant.click()

        chat_with_concierge = page.locator(
            'div[aria-label="Chat with Concierge"][role="menuitem"]'
        )
        expect(chat_with_concierge).to_be_visible()
        chat_with_concierge.click()

        back_arrow_button = page.locator('button[aria-label="Back"]').last
        expect(back_arrow_button).to_be_visible()
        back_arrow_button.click()

        chat_with_concierge = page.locator(
            'div[aria-label="Chat with Concierge"][role="menuitem"]'
        )
        expect(chat_with_concierge).to_be_visible()
