import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright
from playwright.sync_api._context_manager import Playwright
from playwright._impl._browser import Browser
from playwright._impl._page import Page
from playwright._impl._browser_context import BrowserContext
from utils.trace_cleaner import trace_cleaner


# Utility to generate a random email
def generate_random_email():
    # timestamp = int(time.time())
    return f"expensifyapp99887755+{1734479761}@gmail.com"


def login_user(p: Playwright, first_name="Milan", last_name="T") -> tuple[Browser, Page, str, BrowserContext]:
    # Launch chromium and open new page
    galaxy_s8 = p.devices['Galaxy S8']
    browser = p.chromium.launch(headless=True, args=["--ignore-certificate-errors",
                                                     "--disable-web-security",
                                                     "--disable-features=IsolateOrigins,site-per-process"],
                                slow_mo=500)
    context = browser.new_context(
        **galaxy_s8
    )
    # Start tracing
    context.tracing.start(screenshots=True, snapshots=True)

    page = context.new_page()
    user_email = generate_random_email()

    # Step 1: Open expensify url
    page.goto('https://dev.new.expensify.com:8082/')

    # Step 2: Enter email and click continue
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(5000)

    # Step 3: Click join button
    try:
        page.locator('button[tabindex="0"]').click()
        page.wait_for_timeout(5000)
    except Exception:
        pass

    # Step 4: Select 'Track and budget expenses' in onboarding page and click Continue
    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()
    page.wait_for_timeout(4000)

    # Step 5: Enter first name, last name and click continue
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()
    page.wait_for_timeout(2000)

    return browser, page, user_email, context


def create_group_chat(page: Page, users):
    div_get_started_here = page.locator('div:has-text("Get started here!")')
    if div_get_started_here.count() > 0:
        page.locator('button[aria-label="Close"]').last.click()

    # Steps to add multiple users to the group
    for user in users:
        email = user
        # Fill in the email field and click "Add to group"
        input_field = page.locator('input[data-testid="selection-list-text-input"]')
        input_field.fill(email)
        page.wait_for_timeout(1000)
        page.locator('button:has(div:text("Add to group"))').nth(1).click()
        page.wait_for_timeout(1000)

    # Confirm the selection and open the members list
    input_field.press("Enter")
    page.wait_for_timeout(1000)
    page.locator('div[data-testid="selection-list"]').nth(1).press("Enter")
    page.wait_for_timeout(1000)


def delete_user_from_group(page: Page):
    details = page.locator('button[aria-label="Details"]')
    details.click()

    all_members = page.locator('div[aria-label="Members"]')
    all_members.click()

    # select last user to remove from group
    selection_list = page.locator('div[data-testid="selection-list"]')
    delete_last_user = selection_list.locator('button[role="button"]').last
    delete_last_user.click()

    remove_from_group = page.locator('button[role="button"]', has_text='Remove from group')
    remove_from_group.click()

    # delete the last user successfully
    confirm_delete = page.locator('button[data-listener="Enter"]', has_text='Remove')
    confirm_delete.click()

    # Navigate back to group chat
    back_btn_1 = page.locator('button[aria-label="Back"]').last
    back_btn_1.click()

    # Navigate back to group chat
    back_btn_2 = page.locator('button[aria-label="Back"]').last
    back_btn_2.click()


def test_welcome_group_message():
    with sync_playwright() as p:
        browser = None
        context = None
        try:
            first_name = 'Aohn'
            last_name = 'Doe'
            users = [
                'donaldtrump+98@gmail.com',
                'elonmusk+98@gmail.com',
                'pillgates+98@gmail.com',
            ]

            # Step 1: Login user
            browser, page, user_email, context = login_user(p, first_name, last_name)

            # Step 2: Navigate to LHN
            page.get_by_label("Back").click()
            try:
                page.get_by_label("Close").click()
            except:
                pass

            # Step 3: Click on + icon and click on "Start chat"
            page.get_by_label("Start chat (Floating action)").click()
            page.wait_for_timeout(1000)
            page.get_by_text("Start chat").click()
            page.wait_for_timeout(1000)

            # Step 4: Create group chat with 3 users
            create_group_chat(page, users)

            # Step 5: Delete one user from the group
            delete_user_from_group(page)

            # Step 6: check if user email is displayed in welcome message
            welcome_msg = page.locator('div[aria-label="Chat welcome message"]')
            is_user_deleted = welcome_msg.get_by_text(str(users[-1])).is_visible()
            page.wait_for_timeout(2000)

            if is_user_deleted:
                assert False, 'The removed user is displayed in the welcome group message'
            else:
                assert True, 'The removed user is not displayed in the welcome group message'
        except Exception as e:
            # Reraise so that the test failure is visible
            raise e
        finally:
            # Ensure the trace is saved and cleaned no matter what
            if context:
                context.tracing.stop()
                context.tracing.export("/app/expensify/user_tool/output_browser1.zip")
                trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            if browser:
                browser.close()
