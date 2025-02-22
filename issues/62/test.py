from playwright.sync_api import sync_playwright, expect

def generate_random_email():
    return f"nitish.expensify+6874411@gmail.com"


def login_user(pw):
    browser = pw.chromium.launch(proxy = {"server": "http://localhost:8080"}, headless = False, args = ["--no-sandbox", "--disable-dev-shm-usage", "--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"], slow_mo = 2000, channel = "chromium")
    context_args = {}
    context_args["timezone_id"] = "Asia/Calcutta"
    context = browser.new_context(**context_args)
    page = context.new_page()
    user_email = generate_random_email()

    page.goto('https://dev.new.expensify.com:8082/', timeout=3000000)

    page.locator('input[type="email"]').fill(user_email)
    page.get_by_role("button", name="Continue").click()

    try:
        expect(page.get_by_role("button", name="Sign in")
               ).to_be_visible(timeout=3000)
        page.get_by_test_id("validateCode").fill("123456")
    except Exception:
        pass

    return page, browser


def test_the_issue():
    with sync_playwright() as p:
        page, browser = login_user(p)

        page.get_by_label("My settings").click()

        page.get_by_test_id("InitialSettingsPage").get_by_label(
            "Workspaces").click()

        page.get_by_role("button", name="row").click()

        page.get_by_test_id("WorkspaceInitialPage").get_by_label(
            "Company cards").click()

        page.get_by_label("American Express cards").click()

        assert page.get_by_test_id("selection-list").get_by_label(
            "American Express cards").is_visible(), "The bank card name is not the same in feed selector"

        browser.close()
