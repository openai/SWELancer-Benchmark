import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page
from utils.trace_cleaner import trace_cleaner

def login_user(p: PlaywrightContextManager, first_name="Milan", last_name="T") -> tuple[Browser, Page, str]:
    browser = p.chromium.launch(headless=True, args=[
            '--ignore-certificate-errors',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
        ])
    page = browser.new_page()
    user_email = "exxpp001+425425@gmail.com"
    page.goto('https://dev.new.expensify.com:8082/') 
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(2000)

    try: 
        page.locator('button[tabindex="0"]').click() 
        page.wait_for_timeout(4000)
    except Exception:
        pass
    expect(page.locator("text=What do you want to do today?")).to_be_visible()
        
    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()
    page.wait_for_timeout(2000)
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()
    page.wait_for_timeout(2000)
    return browser, page, user_email

def submit_expense_in_workspace_chat(
    browser: Browser, 
    page: Page, 
    user_email: str, 
    amount: str = "1000"
) -> tuple[Browser, Page, str]:
    workspace_chat = page.locator('button[aria-label="Navigates to a chat"]', has_text="Milan T's Workspace")
    expect(workspace_chat).to_be_visible()
    workspace_chat.click()
    page.wait_for_timeout(1000)

    plus_create_icon = page.locator('button[aria-label="Create"]').last
    expect(plus_create_icon).to_be_visible()
    plus_create_icon.click()
 
    submit_expense_button = page.locator('div[aria-label="Submit expense"]')
    expect(submit_expense_button).to_be_visible()
    submit_expense_button.click()

    manual_button = page.locator('button[aria-label="Manual"]')
    expect(manual_button).to_be_visible()
    manual_button.click()
    page.locator('input[role="presentation"]').fill(amount)

    next_button = page.locator('button[data-listener="Enter"]', has_text="Next").first
    expect(next_button).to_be_visible()
    next_button.click()

    merchant_field = page.locator('div[role="menuitem"]', has_text="Merchant")
    expect(merchant_field).to_be_visible()
    merchant_field.click()
    page.locator('input[aria-label="Merchant"]').fill("Test Merchant")
    save_button = page.locator('button', has_text="Save")
    expect(save_button).to_be_visible()
    save_button.click()
    save_button = page.locator('button[data-listener="Enter"]', has_text="Submit")
    expect(save_button).to_be_visible()
    save_button.click()
    return browser, page, user_email

def test_save_description_in_submitted_expense():
    with sync_playwright() as p:
        new_report_title = ''
        browser, page, user_email = login_user(p)
        # Start tracing before the test steps
        page.context.tracing.start(title="output_browser1", screenshots=True, snapshots=True)
        try:
            plus_icon = page.locator('button[aria-label="Start chat (Floating action)"]')
            expect(plus_icon).to_be_visible()
            plus_icon.click()
            page.wait_for_timeout(500)

            new_workspace_button = page.locator('div[aria-label="New workspace"]')
            expect(new_workspace_button).to_be_visible()
            new_workspace_button.click()
            page.wait_for_timeout(500)

            back_arrow_button = page.locator('button[aria-label="Back"]')
            expect(back_arrow_button).to_be_visible()
            back_arrow_button.click()
            page.wait_for_timeout(500)

            inbox_menu = page.locator('button[aria-label="Inbox"]')
            expect(inbox_menu).to_be_visible()
            inbox_menu.click()
            page.wait_for_timeout(500)

            browser, page, user_email = submit_expense_in_workspace_chat(browser, page, user_email)
            browser, page, user_email = submit_expense_in_workspace_chat(browser, page, user_email)
            
            new_workspace_chat = page.locator('button[aria-label="Navigates to a chat"]', has_text="Milan T's Workspace")
            expect(new_workspace_chat).to_be_visible()
            new_workspace_chat.click()
            page.wait_for_timeout(500)
            view_details = page.locator('button[aria-label="View details"]')
            expect(view_details).to_be_visible()
            view_details.click()
            page.wait_for_timeout(500)
            expense_report_button = page.locator('button[aria-label^="Expense Report #"]').nth(1)
            expect(expense_report_button).to_be_visible()
            expense_report_button.click()
            page.wait_for_timeout(500)
            detail_expense_report_button = page.locator('div[aria-label^="Expense Report #"]')
            expect(detail_expense_report_button).to_be_visible()
            detail_expense_report_button.click()
            page.wait_for_timeout(500)
            title_input = page.locator('input[name="text_title"]')
            expect(title_input).to_be_visible()
            title_input.fill(new_report_title)
            page.wait_for_timeout(500)

            save_button = page.locator('button[data-listener="Enter"]', has_text="Save").first
            expect(save_button).to_be_visible()
            save_button.click()
            page.wait_for_timeout(500)
            
            error_field = page.locator("text=This field is required.")
            
            if error_field.is_visible():
                assert True, 'Empty Report title cannot be saved.'
            else:
                assert False, 'Empty Report title has been saved.'
        finally:
            # Stop tracing and export
            page.context.tracing.stop()
            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            page.context.tracing.export(path=trace_path)
            trace_cleaner(trace_path)
            browser.close()
