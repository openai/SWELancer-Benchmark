import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect

def login_user(page, user_email: str, first_name: str, last_name: str):
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(1000)
    try:
        page.locator('button[tabindex="0"]').click()
        page.wait_for_timeout(1000)
    except Exception:
        pass
    expect(page.locator("text=What do you want to do today?")).to_be_visible()
    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()
    page.wait_for_timeout(1000)
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()
    page.wait_for_timeout(1000)

def test_expensify_24381():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=[
            '--ignore-certificate-errors',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
        ],slow_mo=1000)
        page = browser.new_page()

        page.goto('https://dev.new.expensify.com:8082/')
        login_user(page, "testotpverif+243911@gmail.com", "Test", "User")
        page.get_by_label("Start chat (Floating action)").click()
        page.get_by_label("New workspace").click()
        workspace_link = page.url
        page.get_by_label("Back").click()
        page.get_by_label("Subscription").click()
        page.get_by_label("Pay-per-use").click()
        page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()
        page.get_by_role("button", name="row").click()
        page.wait_for_timeout(1000)
        page.get_by_label("Delete").click()
        page.wait_for_timeout(1000)
        page.get_by_role("dialog").get_by_role("button", name="Delete").click()
        page.wait_for_timeout(1000)
        page.goto(workspace_link)
        try:
            page.wait_for_timeout(3000)
            expect(page.get_by_test_id("WorkspacePageWithSections").get_by_role("link", name="Go back to home page")).to_be_visible()
        except:
            page.get_by_text("Members").click()
            page.get_by_test_id("WorkspaceMembersPage").get_by_label("Back").click()
            page.goto(workspace_link)
            expect(page.get_by_test_id("WorkspacePageWithSections").get_by_role("link", name="Go back to home page")).to_be_visible()
