from playwright.sync_api import sync_playwright, expect


def generate_random_email():
    return "nitish.expensify+1740042181@gmail.com"


def login_user(pw):
    browser = pw.chromium.launch(proxy={"server": "http://localhost:8080"}, headless=False, args=[
                                 "--no-sandbox", "--disable-dev-shm-usage", "--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"], slow_mo=2000, channel="chromium")
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
        page.get_by_role("button", name="Join").click()

    return page, browser


def test_the_issue():
    with sync_playwright() as p:
        page, browser = login_user(p)

        page.get_by_label("My settings").click()

        page.get_by_test_id("InitialSettingsPage").get_by_label(
            "Workspaces").click()

        page.locator("button").filter(has_text="dummy_ws.default-").click()

        page.set_viewport_size({"width": 355, "height": 627})

        page.get_by_test_id(
            "WorkspacePageWithSections").get_by_label("Back").click()

        page.set_viewport_size({"width": 900, "height": 627})
        page.wait_for_timeout(10000)

        assert page.get_by_test_id("WorkspacePageWithSections").get_by_text("Profile").is_visible(
        ), "Workspace profile is not displayed in the central pane after resizing"

        browser.close()
