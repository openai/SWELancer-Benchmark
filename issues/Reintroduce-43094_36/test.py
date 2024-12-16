import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect


def login_member(p) -> tuple:
    browser = p.chromium.launch(headless=True, args=[
        "--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"],
        slow_mo=2000)
    context_args = {}
    context_args["timezone_id"] = "Asia/Calcutta"
    context = browser.new_context(**context_args)
    page = context.new_page()

    user_email2 = "nitish.expensify+1734093815@gmail.com"

    page.goto('https://dev.new.expensify.com:8082/')
    page.locator('input[type="email"]').fill(user_email2)
    page.locator('button[tabindex="0"]').click()

    try:
        expect(page.get_by_role("button", name="Sign in")).to_be_visible()
        page.get_by_test_id("validateCode").fill("123456")
    except Exception:
        page.get_by_role("button", name="Join").click()

    return browser, page


def login_admin(p) -> tuple:
    browser = p.chromium.launch(headless=True, args=[
        "--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"],
        slow_mo=1000)
    context_args = {}
    context_args["timezone_id"] = "Asia/Calcutta"
    context = browser.new_context(**context_args)
    page = context.new_page()

    # Generate admin email and work name
    admin_email = "nitish.expensify+1734093834@gmail.com"

    page.goto('https://dev.new.expensify.com:8082/')
    page.locator('input[type="email"]').fill(admin_email)
    page.locator('button[tabindex="0"]').click()

    try:
        expect(page.get_by_role("button", name="Sign in")).to_be_visible()
        page.get_by_test_id("validateCode").fill("123456")
    except Exception:
        page.get_by_role("button", name="Join").click()

    return browser


def check_name_change(page):
    page.get_by_label("Find something...").click()
    page.get_by_test_id("selection-list-text-input").fill("room1")
    page.wait_for_selector('button[aria-label="#room1"]', state='visible')
    button = page.locator('button[aria-label="#room1"]').count()
    assert button == 1, "Expected 1 button with aria-label '#room1'"


def test_run():
    with sync_playwright() as p:
        browser_member, page_member = login_member(p)

        browser_admin = login_admin(p)

        check_name_change(page_member)

        browser_admin.close()
        browser_member.close()


if __name__ == "__main__":
    test_run()
