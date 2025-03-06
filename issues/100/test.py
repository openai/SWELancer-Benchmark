from playwright.sync_api import sync_playwright, expect
from playwright._impl._browser import Browser
from playwright._impl._page import Page
from playwright.sync_api._context_manager import PlaywrightContextManager

# Expensify app URL
NEWDOT_URL = "https://dev.new.expensify.com:8082"
OLDDOT_URL = "http://127.0.0.1:9000/"

def login_user(p: PlaywrightContextManager, email, first_name="Milan", last_name="T") -> tuple[Browser, Page, str]:
    # Launch chromiun and open new page
    browser = p.chromium.launch(headless=False, args=[
        "--ignore-certificate-errors",
        "--disable-web-security",
        "--disable-features=IsolateOrigins,site-per-process"
    ], slow_mo=1000, proxy = {"server": "http://127.0.0.1:8080/"})
    context = browser.new_context()
    page = context.new_page()

    # Step 1: Open expensify url
    page.goto('https://dev.new.expensify.com:8082/') 

    # Step 2: Enter email and click continue
    page.locator('input[type="email"]').fill(email)
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(1000)

    # Step 3: Click join button
    page.get_by_role("button", name="Join").click()

    if(page.locator("text='Track and budget expenses'").is_visible() == False):
        page.reload()
        
    # Step 4: Select 'Track and budget expenses' in onobarding page and click Continue
    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()
    page.wait_for_timeout(1000)

    # Step 5: Enter first name, last name and click continue
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()
    page.wait_for_timeout(1000)

    return browser, page, email

def test_same_workspace_name_issue():
    with sync_playwright() as pw:
        email1 = "rgarciatammy4+jopu8yhuoijo8ui@gmail.com"
        email2 = "rgarciatammy4+hboiju8uigbhjkl@gmail.com"
        browser1, page1, email1 = login_user(pw,email1, "Test1", "User1")
        browser2, page2, email2 = login_user(pw,email2, "Test2", "User2")
        page1.wait_for_timeout(3000)
        page1.get_by_label("My settings").click()
        page1.wait_for_timeout(3000)
        page1.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()
        page1.wait_for_timeout(3000)
        page1.get_by_label("New workspace").click()
        page1.wait_for_timeout(3000)
        page1.get_by_test_id("WorkspacePageWithSections").get_by_text("Test1 User1's Workspace", exact=True).click()
        page1.wait_for_timeout(3000)
        page1.get_by_role("textbox", name="Name").press("ControlOrMeta+a")
        page1.wait_for_timeout(3000)
        page1.get_by_role("textbox", name="Name").fill("Approvers testing 2")
        page1.wait_for_timeout(3000)
        page1.get_by_role("button", name="Save").click()
        page1.wait_for_timeout(3000)
        page1.get_by_label("Members").click()
        page1.wait_for_timeout(3000)
        page1.get_by_role("button", name="Invite member").click()
        page1.wait_for_timeout(3000)
        page1.get_by_test_id("selection-list-text-input").fill(email2)
        page1.wait_for_timeout(3000)
        page1.get_by_text(email2).first.click()
        page1.wait_for_timeout(3000)
        page1.get_by_role("button", name="Next").click()
        page1.wait_for_timeout(3000)
        page1.get_by_test_id("WorkspaceInviteMessagePage").get_by_role("button", name="Invite").click()
        page1.wait_for_timeout(3000)
        page1.get_by_label("Back").click()
        page1.wait_for_timeout(3000)
        page1.get_by_label("Inbox").click()
        page1.wait_for_timeout(3000)

        page2.reload()
        page1.wait_for_timeout(3000)
        page2.get_by_label("Start chat (Floating action)").click()
        page1.wait_for_timeout(3000)
        page2.get_by_label("Create expense").click()
        page1.wait_for_timeout(3000)
        page2.get_by_label("Manual").click()
        page1.wait_for_timeout(3000)
        page2.get_by_placeholder("0").fill("5000")
        page1.wait_for_timeout(3000)
        page2.locator("#numPadContainerView").get_by_role("button", name="Next").click()
        page1.wait_for_timeout(3000)
        page2.get_by_test_id("selection-list").get_by_label("Test2 User2").click()
        page1.wait_for_timeout(3000)
        page2.get_by_role("menuitem", name="Merchant Required").click()
        page1.wait_for_timeout(3000)
        page2.get_by_role("textbox", name="Merchant").fill("m1")
        page1.wait_for_timeout(3000)
        page2.get_by_role("button", name="Save").click()
        page1.wait_for_timeout(3000)
        page2.get_by_role("button", name="Submit").click()
        page1.wait_for_timeout(3000)
        page2.get_by_label("View details").click()
        page1.wait_for_timeout(3000)
        page2.get_by_label("From Test2 User2 in Approvers").click()
        page1.wait_for_timeout(3000)
        page2.get_by_label("View details").click()
        page1.wait_for_timeout(3000)
        expect(page2.get_by_text("From Approvers testing 2 in Approvers testing 2", exact=True)).not_to_be_visible()

        # Close the browser
        browser1.close()
        browser2.close()