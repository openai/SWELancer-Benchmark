import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import Page, expect, sync_playwright


def create_user(
    page: Page, firstname: str, lastname: str, email: str
):
    # Sign up
    page.get_by_test_id("username").fill(email)
    page.wait_for_timeout(1000)
    page.get_by_role("button", name="Continue").click()
    page.wait_for_timeout(1000)
    page.get_by_role("button", name="Join").click()

    # Update profile
    page.get_by_text("Track and budget expenses").click()
    page.get_by_role("textbox", name="First name").fill(firstname)
    page.get_by_role("textbox", name="Last name").fill(lastname)
    page.wait_for_timeout(1000)
    page.get_by_role("button", name="Continue").click()
    return email


def test_task_preview():

    with sync_playwright() as p:
        # Launch chromium and open new page
        browser = p.chromium.launch(headless=True, slow_mo = 1000,
            proxy = {"server": "http://127.0.0.1:8080/"},
            args=[
            "--ignore-certificate-errors",
            "--disable-web-security", 
            "--disable-features=IsolateOrigins,site-per-process"
        ])
        context_args = {}
        context_args["geolocation"] = {"latitude": 37.7749, "longitude": 122.4194}
        context_args["permissions"] = ["geolocation"]
        context_args["viewport"] = {"width": 1280, "height": 800}
        context_args["user_agent"] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.36"
        context_args["ignore_https_errors"] = True
        context = browser.new_context(**context_args)

        # Create a new page in the appropriate context
        page = context.new_page()
        page.wait_for_timeout(5000)

        page.goto("https://127.0.0.1:8082/")

        # create user
        email1 = create_user(page, "Test", "User1", "t1533148+1734358702@gmail.com")
        context1 = browser.new_context(**context_args)
        page1 = context1.new_page()
        page1.wait_for_timeout(5000)

        page1.goto("https://127.0.0.1:8082/")
        email2 = create_user(page1, "Test", "User2", "t1533148+1734358725@gmail.com")
        page.wait_for_timeout(2000)
        page.get_by_label("My settings").click()
        page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()
        page.get_by_label("New workspace").last.click()
        page.get_by_label("Members").click()
        page.get_by_role("button", name="Invite member").click()
        
        page.get_by_test_id("selection-list-text-input").fill(email2)
        page.get_by_label("Test User2").last.click()
        page.get_by_role("button", name="Next").click()
        page.get_by_test_id("WorkspaceInviteMessagePage").get_by_role("button", name="Invite").click()
        page.get_by_label("More features").click()
        page.get_by_label("Configure how spend is").click()
        page.get_by_label("Workflows").click()
        page.get_by_label("Require additional approval").click()
        page.get_by_label("Back").click()
        page.get_by_label("Inbox").click()
        
        page1.wait_for_timeout(2000)
        page1.reload()
        page1.locator('button[aria-label="Navigates to a chat"]', has_text="Test User1's Workspace").last.click()
        page1.get_by_label("Create").nth(-1).click()
        page1.get_by_label("Submit expense").click()
        page1.get_by_label("Manual").click()
        page1.get_by_placeholder("0").fill("100")
        page1.locator("#numPadContainerView").get_by_role("button", name="Next").click()
        page1.locator('div[role="menuitem"]', has_text="Merchant").click()
        page1.locator('input[aria-label="Merchant"]').fill("Test Merchant")
        page1.locator('button', has_text="Save").click()
        page1.locator("button", has_text="Submit ₹").last.click()
        page1.get_by_label("View details").click()
        page1.wait_for_timeout(2000)
        current_page_url = page1.url
        page1.goto(f'{current_page_url}/details')
        page1.get_by_role("button", name="Hold").click()
        page1.get_by_role("textbox", name="Reason").fill("NA")
        page1.get_by_role("button", name="Hold expense").click()
        page1.get_by_role("button", name="Got it").click()
        page.wait_for_timeout(2000)
        page.reload()
        page.locator('button[aria-label="Navigates to a chat"]', has_text="Test User2").last.click()
        page.wait_for_timeout(2000)
        page.get_by_role("button", name="Approve").click()
        page.wait_for_timeout(5000)
        expect(page.locator("text=Approve what's not on hold, or approve the entire report.")).not_to_be_visible()


        # ---------------------
        page1.close()
        page.close()
        context1.close()
        context.close()
        browser.close()