import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page
from utils.trace_cleaner import trace_cleaner

# Utility to generate a random email
def generate_random_email():
    return f"expensifyapp97+0090@gmail.com"


def login_user(p: PlaywrightContextManager, first_name="Milan", last_name="T") -> tuple[Browser, "BrowserContext", Page, str]:
    # Launch chromium and open new context + page
    proxy = {"server": "http://127.0.0.1:8080/"}
    args = ["--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"]

    browser = p.chromium.launch(headless=True, args=args, proxy=proxy)
    context = browser.new_context()
    page = context.new_page()
    user_email = generate_random_email()

    # Step 1: Open expensify url
    page.goto('https://dev.new.expensify.com:8082/')

    # Step 2: Enter email and click continue
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(2000)

    # Step 3: Click join button
    try:
        page.locator('button[tabindex="0"]').click()
        time.sleep(4)
    except Exception:
        pass

    if page.locator("text='What do you want to do today?'").count() == 1:
        # Step 4: Select 'Track and budget expenses' in onboarding page and click Continue
        page.locator("text='Track and budget expenses'").click()
        page.get_by_role("button", name="Continue").click()
        page.wait_for_timeout(2000)

        # Step 5: Enter first name, last name and click continue
        page.locator('input[name="fname"]').fill(first_name)
        page.locator('input[name="lname"]').fill(last_name)
        page.get_by_role("button", name="Continue").last.click()
        page.wait_for_timeout(2000)
    else:
        page.locator('button[aria-label="My settings"]').click()
        page.get_by_label(user_email).first.click()
        page.get_by_role("textbox", name="First name").click()
        page.get_by_role("textbox", name="First name").fill(first_name)
        page.get_by_role("textbox", name="Last name").click()
        page.get_by_role("textbox", name="Last name").fill(last_name)
        page.get_by_role("button", name="Save").click()
        page.locator('button[aria-label="Inbox"]').click()

    return browser, context, page, user_email


def test_gmail_user_pay():
    with sync_playwright() as p:
        # Step 1: Login user
        browser, context, page, user_email = login_user(p)
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        try:
            test_email = f"expensifyapp9988775511@gmail.com"

            # Step 2: Click on + icon and click on "New workspace"
            plus_icon = page.locator('button[aria-label="Start chat (Floating action)"]')
            expect(plus_icon).to_be_visible()
            plus_icon.click()
            page.wait_for_timeout(2000)

            start_chat = page.locator('div[aria-label="Start chat"]')
            expect(start_chat).to_be_visible()
            start_chat.click()
            page.wait_for_timeout(2000)

            # Step 3: Search user to start a 1:1 chat
            search_email = page.locator('input[aria-label="Name, email, or phone number"]')
            expect(search_email).to_be_visible()
            search_email.fill(test_email)
            page.wait_for_timeout(2000)
            search_email.click()
            page.wait_for_timeout(2000)

            select_email = page.locator(f'button[aria-label="{test_email}"]')
            expect(select_email).to_be_visible()
            select_email.click()
            page.wait_for_timeout(4000)

            # Step 4: Create and pay user
            create_pay_expense = page.locator('button[aria-label="Create"]').last
            expect(create_pay_expense).to_be_visible()
            create_pay_expense.click()

            pay_expense = f'Pay {test_email}'
            pay = page.get_by_text(pay_expense)
            pay.click()
            page.wait_for_timeout(2000)

            # Step 5: Choose currency
            currency = page.locator('button[aria-label="Select a currency"]')
            expect(currency).to_be_visible()
            currency.click()

            search_currency = page.locator('input[aria-label="Search"]')
            search_currency.fill('USD')
            choose_usd = page.locator('button[aria-label="USD - $"]')
            expect(choose_usd).to_be_visible()
            choose_usd.click()

            # Step 5: Enter amount
            amount = page.locator('input[placeholder="0"]')
            expect(amount).to_be_visible()
            amount.fill('100')

            # Step 6: Choose pay option: 'Pay with expensify'
            next_button = page.locator('button[data-listener="Enter"]', has_text="Next")
            expect(next_button).to_be_visible()
            next_button.click()
            page.wait_for_timeout(2000)

            pay_with_expensify = page.locator('button[data-listener="Enter"]', has_text="Pay with Expensify")
            expect(pay_with_expensify).to_be_visible()
            pay_with_expensify.click()
            page.wait_for_timeout(2000)

            # Step 7: Check Not here page
            not_here_page = page.get_by_text("Oops, this page cannot be found")

            if not_here_page.is_visible():
                assert False, 'Not here page opens when Gmail user Pay with Expensify'
            else:
                assert True, 'Not here page does not open when Gmail user Pay with Expensify'

            page.wait_for_timeout(3000)

        except Exception as e:
            # Re-raise so pytest sees the failure
            raise e
        finally:
            # Stop tracing and clean
            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            browser.close()
}