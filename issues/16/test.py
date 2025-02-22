from playwright.sync_api import sync_playwright

def launch_browser(playwright):
    browser = playwright.chromium.launch(
            channel="chrome",
            headless=False,
            slow_mo=750,
            proxy={"server": "http://localhost:8080"},
            args=[
                "--ignore-certificate-errors",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process"
            ]
        )
    
    context = browser.new_context(timezone_id = "Asia/Karachi")
    page = context.new_page()

    return browser, page

def login_user(page, first_name="Test", last_name="User"):

    page.goto("https://dev.new.expensify.com:8082/")

    user_email = "freelancer.test.exp+1740172456@gmail.com"

    page.get_by_test_id("username").fill(user_email)
    page.get_by_role("button", name="Continue").click()
    page.get_by_role("button", name="Join").click()
    page.get_by_text("Track and budget expenses").click()
    page.get_by_role("button", name="Continue").click()
    page.get_by_role("textbox", name="First name").fill(first_name)
    page.get_by_role("textbox", name="Last name").fill(last_name)
    page.get_by_role("form").get_by_role("button", name="Continue").click()


def test_example():
    with sync_playwright() as playwright:

        browser, page = launch_browser(playwright)
        login_user(page)

        page.get_by_label("Start chat (Floating action)").click()
        page.get_by_test_id("PopoverMenuItem-New workspace").click()
        page.get_by_label("Members").click()
        page.get_by_role("button", name="Invite member").click()
        page.get_by_test_id("selection-list-text-input").fill("randomgenmail+55555@gmail.com")
        page.get_by_label("randomgenmail+55555@gmail.com").first.click()
        page.get_by_test_id("selection-list-text-input").fill("randomgenmail+66666@gmail.com")
        page.get_by_label("randomgenmail+66666@gmail.com").first.click()
        page.get_by_role("button", name="Next").click()
        page.get_by_test_id("WorkspaceInviteMessagePage").get_by_role("button", name="Invite").click()
        page.get_by_label("Back").click()
        page.get_by_label("Inbox").click()
        page.get_by_test_id("WorkspaceSwitcherButton").click()
        page.get_by_label("Test User's Workspace").click()
        page.get_by_label("Start chat (Floating action)").click()
        page.get_by_test_id("PopoverMenuItem-Create expense").click()
        page.get_by_label("Manual").click()
        page.get_by_placeholder("0").fill("100")
        page.locator("#numPadContainerView").get_by_role("button", name="Next").click()

        assert page.get_by_label("Test User's Workspace").count() == 1

        browser.close()