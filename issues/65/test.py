import time
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page

# Utility to generate a random email
def generate_random_email():
    return f"testerbro7077+45756976678@gmail.com"

# Login as member and fill in personal details
def login_member_a(p, membera_first_name: str, membera_last_name: str) -> tuple:
    browser = p.chromium.launch(
        proxy = {"server": "http://localhost:8080"}, headless = False, args = ["--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"], slow_mo = 500, channel = "chromium")

    context = browser.new_context()
    page = context.new_page()


    user_email2 = generate_random_email()

    page.goto('https://dev.new.expensify.com:8082/')
    page.locator('input[type="email"]').fill(user_email2)
    page.get_by_role("button", name="Continue").click()
    page.wait_for_timeout(1000)

    try:
        page.get_by_role("button", name="Join").click()
        page.wait_for_timeout(1000)
    except Exception:
        pass
    expect(page.locator("text=What do you want to do today?")).to_be_visible()
    page.wait_for_timeout(1000)

    page.get_by_text("Track and budget expenses").click()

    page.locator('input[name="fname"]').fill(membera_first_name)
    page.locator('input[name="lname"]').fill(membera_last_name)
    page.get_by_role("button", name="Continue").last.click()
    page.wait_for_timeout(1000)

    return browser, page, user_email2

def added_features_check(page):
    page.get_by_label("My settings").click()
    page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").get_by_text("Workspaces").click()
    page.get_by_label("New workspace").click()
    assert page.get_by_test_id("WorkspaceInitialPage").get_by_text("Workspace profile").is_visible(), "profile is not chnged to Workspace profile in the LHN"
    assert page.get_by_test_id("WorkspacePageWithSections").get_by_text("Workspace profile").is_visible(), "Profile is not changed to Workspace profile in title"
    assert page.locator("#simple-illustration__building_svg__Layer_1 path").first.is_visible(), "Workspace profile is not changed in the illustration"
    ws_name = page.get_by_test_id("WorkspacePageWithSections").get_by_text("Workspace name")
    assert ws_name.is_visible(), "Name is not changed to Workspace name"
    ws_name.click()
    assert page.get_by_text("Workspace name").nth(2).is_visible(), "Name is not changed to Workspace name in name edit page"


def test_run(membera_first_name="Sai", membera_last_name="Yagna"):
    with sync_playwright() as p:

        browser_membera, page_membera, user_email2 = login_member_a(p, membera_first_name, membera_last_name)
        added_features_check(page_membera)

        

        browser_membera.close()


if __name__ == "__main__":
    test_run()