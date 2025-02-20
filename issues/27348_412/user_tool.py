import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from playwright._impl._browser import Browser
from playwright._impl._page import Page
from utils.trace_cleaner import trace_cleaner

static_email = "testuserexpensify1+81@gmail.com"


def login_user(page: Page, first_name="Milan", last_name="T") -> tuple[Page, str]:

    user_email = static_email


    page.goto('https://dev.new.expensify.com:8082/') 


    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(1000)


    try: 
        page.locator('button[tabindex="0"]').click() 
    except Exception:
        pass
            

    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()


    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()

    return page, user_email


def create_new_workspace(
    browser: Browser, 
    page: Page, 
    user_email: str, 
) -> tuple[Browser, Page, str]:

    plus_icon = page.locator('button[aria-label="Start chat (Floating action)"]')
    plus_icon.click()

    new_workspace_button = page.locator('div[aria-label="New workspace"]')
    new_workspace_button.click()


    back_arrow_button = page.locator('button[aria-label="Back"]')
    back_arrow_button.click()

    return browser, page, user_email


def track_expense_in_workspace(
    page: Page, 
    amount: str = "1000"
) -> Page:

    inbox = page.locator('button[aria-label="Inbox"]')
    inbox.click()


    personal_chat = page.get_by_text("Milan T (you)")
    personal_chat.click()


    plus_icon = page.locator('button[aria-label="Start chat (Floating action)"]')
    plus_icon.click()


    submit_expense_button = page.locator('div[aria-label="Submit expense"]')
    submit_expense_button.click()


    manual_button = page.locator('button[aria-label="Manual"]')
    manual_button.click()

    page.locator('input[role="presentation"]').fill(amount)


    next_button = page.locator('button[data-listener="Enter"]', has_text="Next").first
    next_button.click()


    next_button = page.locator('button[aria-label="Milan T\'s Workspace"][tabindex="0"]').last
    next_button.click()


    merchant = page.locator('div[role="menuitem"]', has_text="Merchant")
    merchant.click()

    page.locator('input[aria-label="Merchant"]').fill("aaa@example.com")


    save_button = page.locator('button[data-listener="Enter"]', has_text="Save")
    save_button.click()


    save_button = page.locator('button[data-listener="Enter"]', has_text="Submit")
    save_button.click()

    return page


def change_subscription_to_pay_per_use(
    page: Page, 
) -> Page:

    my_settings = page.locator('button[aria-label="My settings"]')
    my_settings.click()


    subscription = page.locator('div[aria-label="Subscription"][role="menuitem"]')
    subscription.click()


    pay_per_use = page.locator('button[aria-label="Pay-per-use"]')
    pay_per_use.click()

    return page


def delete_workspace(
    page: Page, 
) -> Page:

    my_settings = page.locator('button[aria-label="My settings"]')
    my_settings.click()


    workspaces = page.locator('div[aria-label="Workspaces"][role="menuitem"]')
    workspaces.click()


    button = page.get_by_role("button", name="row")
    button.click()


    delete = page.locator('button[aria-label="Delete"]')
    delete.click()


    delete = page.locator('button[data-listener="Enter"]', has_text="Delete")
    delete.click()

    return page


def test_green_icon_on_lhn():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, slow_mo=1000, args=["--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"])
        context = browser.new_context()


        context.tracing.start(screenshots=True, snapshots=True)
        page = context.new_page()

        try:

            page, user_email = login_user(page)


            browser, page, user_email = create_new_workspace(browser, page, user_email)


            page = track_expense_in_workspace(page)


            page = change_subscription_to_pay_per_use(page)


            page = delete_workspace(page)


            inbox = page.locator('button[aria-label="Inbox"]')
            inbox.click()


            archived = page.locator('button[aria-label="Navigates to a chat"]', has_text="Milan T\'s Workspace (archived)")
            circle_svg = archived.locator('svg circle')
            expect(circle_svg).not_to_be_visible()

        finally:

            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")


            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")

            context.close()
            browser.close()
