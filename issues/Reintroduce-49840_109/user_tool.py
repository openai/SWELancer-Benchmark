import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._browser_context import BrowserContext
from playwright._impl._page import Page

# Utility to generate a random email
def generate_email():
    timestamp = "891832"
    return f"f20022+{timestamp}@gmail.com"


def login_user(p: PlaywrightContextManager, first_name="Alif", last_name="F") -> tuple[Browser, BrowserContext, Page, str]:
    # Launch chromium and create context
    browser = p.chromium.launch(
        channel="chrome",
        headless=True,
        args=[
            "--ignore-certificate-errors",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ],
        proxy={"server": "http://localhost:8080"},
        slow_mo=500
    )

    # Create a new context and page
    context = browser.new_context()
    page = context.new_page()
    user_email = generate_email()

    # Step 1: Open expensify url
    page.goto('https://dev.new.expensify.com:8082/') 

    # Step 2: Enter email and click continue
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(5000)

    # Step 3: Click join button
    try:
        page.locator('button[tabindex="0"]').click()
        page.wait_for_timeout(2000)
    except Exception:
        pass
    expect(page.locator("text=What do you want to do today?")).to_be_visible()

    # Step 4: Select 'Track and budget expenses' in onobarding page and click Continue
    page.locator("text='Track and budget expenses'").click()
    page.wait_for_timeout(2000)

    # Step 5: Enter first name, last name and click continue
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()
    page.wait_for_timeout(2000)

    return browser, context, page, user_email


def submit_expense_in_spanish(page: Page):

    # Step 1: Click on create and choose submit expense
    create_submit_exp = page.locator('button[aria-label="Crear"]')
    expect(create_submit_exp).to_be_visible()
    create_submit_exp.click()
    page.wait_for_timeout(2000)

    submit_expense = page.locator('div[aria-label="Presentar gasto"]')
    expect(submit_expense).to_be_visible()
    submit_expense.click()
    page.wait_for_timeout(2000)

    choose_manual = page.locator('button[aria-label="Manual"]')
    expect(choose_manual).to_be_visible()
    choose_manual.click()
    page.wait_for_timeout(2000)

    page.locator('input[role="presentation"]').fill('765')
    page.wait_for_timeout(2000)

    # Step 2: Click on Next button
    next_button = page.locator('button[data-listener="Enter"]', has_text="Siguiente").first
    expect(next_button).to_be_visible()
    next_button.click()
    page.wait_for_timeout(2000)

    # Step 3: Add merchant details
    merchant_field = page.locator('div[role="menuitem"]', has_text="Comerciante")
    expect(merchant_field).to_be_visible()
    merchant_field.click()
    page.wait_for_timeout(2000)

    page.locator('input[aria-label="Comerciante"]').fill("XYZ")

    save_button = page.locator('button', has_text="Guardar")
    expect(save_button).to_be_visible()
    save_button.click()
    page.wait_for_timeout(2000)

    # Step 4: Submit the expense
    save_button = page.locator('button[data-listener="Enter"]', has_text="Solicitar")
    expect(save_button).to_be_visible()
    save_button.click()
    page.wait_for_timeout(2000)


def test_close_account_bottom_margin():
    with sync_playwright() as p:
        first_name = 'Milan'
        last_name = 'T'
        
        # Step 1: Login user
        browser, context, page, user_email = login_user(p, first_name, last_name)

        # Start tracing
        context.tracing.start(screenshots=True, snapshots=True, sources=True)

        try:
            # Step 2: Click on + icon and click on "New workspace"
            plus_icon = page.locator('button[aria-label="Start chat (Floating action)"]')
            expect(plus_icon).to_be_visible()
            plus_icon.click()
            page.wait_for_timeout(2000)

            # Step 3: Create New Workspace
            new_workspace_button = page.locator('div[aria-label="New workspace"]')
            expect(new_workspace_button).to_be_visible()
            new_workspace_button.click()
            page.wait_for_timeout(2000)

            # Step 4: Go Back to Main Menu
            back_btn = page.locator('button[aria-label="Back"]')
            expect(back_btn).to_be_visible()
            back_btn.click()
            page.wait_for_timeout(1000)

            # Step 5: Naviagte to settings and change language
            settings = page.locator('button[aria-label="My settings"]')
            expect(settings).to_be_visible()
            settings.click()
            page.wait_for_timeout(2000)

            open_preference = page.locator('div[aria-label="Preferences"]')
            expect(open_preference).to_be_visible()
            open_preference.click()
            page.wait_for_timeout(2000)

            select_language = page.locator('div[aria-label="English"]')
            expect(select_language).to_be_visible()
            select_language.click()

            choose_spanish = page.locator('button[aria-label="Spanish"]')
            expect(choose_spanish).to_be_visible()
            choose_spanish.click()

            inbox = page.locator('button[aria-label="Recibidos"]')
            expect(inbox).to_be_visible()
            inbox.click()
            page.wait_for_timeout(2000)

            # Step 6: Submit an expense in spanish language
            submit_expense_in_spanish(page)

            # Step 7: Pay expense 
            pay_expense = page.locator('button[role="button"]').nth(18)
            expect(pay_expense).to_be_visible()
            pay_expense.click()
            page.wait_for_timeout(3000)

            select_payment = page.get_by_text('de otra forma')
            expect(select_payment).to_be_visible()
            select_payment.click()
            page.wait_for_timeout(3000)

            confirm_pay_expense = page.locator('button[role="button"]', has_text='de otra forma').last
            expect(confirm_pay_expense).to_be_visible()
            confirm_pay_expense.click()

            # Step 8: Check if payment completed is in spanish or not
            payment_complete = page.get_by_text('Payment complete')

            if payment_complete.is_visible():
                assert False, '"Payment completed" should be in Spanish'
            else:
                assert True, '"Payment completed" is in Spanish'

            page.wait_for_timeout(4000)

        except Exception as e:
            # Stop & export trace even if test fails
            context.tracing.stop()
            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            context.tracing.export(trace_path)
            from utils.trace_cleaner import trace_cleaner
            trace_cleaner(trace_path)
            # re-raise the exception
            raise e
        else:
            # Stop & export trace if test passes
            context.tracing.stop()
            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            context.tracing.export(trace_path)
            from utils.trace_cleaner import trace_cleaner
            trace_cleaner(trace_path)
        finally:
            context.close()
            browser.close()
