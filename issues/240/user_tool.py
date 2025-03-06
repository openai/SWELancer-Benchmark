import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright
from utils.trace_cleaner import trace_cleaner


def generate_random_email1(base_email="testerbro7077@gmail.com"):
    timestamp = int("46344")
    email_user, domain = base_email.split('@')
    return f"{email_user}+{timestamp}@{domain}"


def login_user1(p, first_name="Yagna", slow_mo=1000, last_name="Sai") -> tuple:
    user_email1 = generate_random_email1()
    password = ""
    
    browser = p.chromium.launch(headless=True, args=[
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
        ])
    context = browser.new_context()
    context.tracing.start(screenshots=True, snapshots=True, sources=True)
    page = context.new_page()

    page.goto('https://dev.new.expensify.com:8082/') 
    phone_or_email_input = page.locator('input[type="email"]')
    phone_or_email_input.fill(user_email1)

    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(1000)

    validate_code_input = page.locator('input[name="validateCode"]').nth(0)
    validate_code_input.fill("123456")

    return browser, context, page, user_email1


def generate_random_email2(base_email="testerbro7077@gmail.com"):
    timestamp = int("46345")
    email_user, domain = base_email.split('@')
    return f"{email_user}+{timestamp}@{domain}"


def login_user2(p, first_name="Yagna", last_name="Sai") -> tuple:
    user_email2 = generate_random_email2()
    password = ""
    
    browser = p.chromium.launch(headless=True, args=[
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
        ])
    context = browser.new_context()
    context.tracing.start(screenshots=True, snapshots=True, sources=True)
    page = context.new_page()

    page.goto('https://dev.new.expensify.com:8082/') 
    phone_or_email_input = page.locator('input[type="email"]')
    phone_or_email_input.fill(user_email2)

    page.locator('button[tabindex="0"]').click()

    validate_code_input = page.locator('input[name="validateCode"]').nth(0)
    validate_code_input.fill("123456")

    return browser, context, page, user_email2


def add_member(page):
    page.get_by_label("My settings").click()
    page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").get_by_text("Workspaces").click()
    page.get_by_test_id("WorkspacesListPage").locator("button").filter(has_text="Testerbro7077+46345@gmail.com").get_by_label("More").click()
    assert not page.get_by_text("Delete Workspace").is_visible()
    page.mouse.click(0.5 * page.viewport_size['width'], 0.5 * page.viewport_size['height'])
    page.get_by_test_id("WorkspacesListPage").locator("button").filter(has_text="Testerbro7077+46345@gmail.com").click()
    assert not page.get_by_label("Delete").is_visible()


def test_run(admin_first_name="Yagna", admin_last_name="Sai", member_first_name="Sai", member_last_name="Yagna"):
    with sync_playwright() as p:
        # Launch both browsers and start tracing
        browser_member, context_member, page_member, user_email1 = login_user1(p, member_first_name, member_last_name)
        browser_admin, context_admin, page_admin, admin_email = login_user2(p, admin_first_name, admin_last_name)

        try:
            add_member(page_member)
        finally:
            # Stop tracing for admin browser, export and clean the trace
            context_admin.tracing.stop(path="/app/expensify/user_tool/output_browser2.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser2.zip")
            browser_admin.close()

            # Stop tracing for member browser, export and clean the trace
            context_member.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            browser_member.close()


if __name__ == "__main__":
    test_run()
