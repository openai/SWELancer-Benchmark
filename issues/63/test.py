import time
import re 
from playwright.sync_api import sync_playwright, expect
def login_member_a(p, membera_first_name: str, membera_last_name: str) -> tuple:
    browser = p.chromium.launch(proxy={"server": "http://localhost:8080"}, headless = False, args = ["--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"], slow_mo = 1000, channel = "chromium")
    pixel_5 = p.devices['Pixel 5']
    context = browser.new_context(**pixel_5)
    page = context.new_page()

    user_email2 = "testerbro7077+hfjdjg@gmail.com"
    page.goto('https://dev.new.expensify.com:8082/')
    page.get_by_test_id("username").click()
    page.get_by_test_id("username").fill(user_email2)
    page.get_by_role("button", name="Continue").click()
    page.get_by_role("button", name="Join").click()
    page.get_by_text("Track and budget expenses").click()
    page.get_by_role("textbox", name="First name").fill(membera_first_name)
    page.get_by_role("textbox", name="Last name").click()
    page.get_by_role("textbox", name="Last name").fill(membera_last_name)
    page.get_by_role("button", name="Continue").click()
    page.wait_for_timeout(1000)

    return browser, page, user_email2

def check_color(page):
    page.get_by_label("Back").click()
    page.get_by_label("My settings").click()
    page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").get_by_text("Workspaces").click()
    page.get_by_label("New workspace").click()
    page.get_by_text("More features").click()
    page.get_by_label("Classify costs and track").click()
    page.get_by_text("Tags").click()
    page.get_by_role("button", name="Add tag").click()
    page.get_by_role("textbox", name="Name").fill("1 : ghhhg8gugigiigiggiigiggiigguguigtiyiy8gigigiigy9giigigigig : huigigjggiigkbbjhj : 🥰😘😘")
    page.get_by_role("button", name="Save").click()
    page.get_by_test_id("WorkspaceTagsPage").get_by_label("Back").click()
    page.get_by_test_id("WorkspaceInitialPage").get_by_label("Back").click()
    page.get_by_label("Back").click()
    page.get_by_label("Inbox").click()
    page.locator('button[aria-label="Navigates to a chat"]').nth(3).click()
    page.get_by_label("Create").click()
    try:
        page.get_by_text("Create expense").click()
    except:
        page.get_by_text("Submit expense").nth(2).click()
    page.get_by_label("Manual").click()
    page.get_by_placeholder("0").fill("100")
    page.locator("#numPadContainerView").get_by_role("button", name="Next").click()
    page.get_by_text("Merchant").click()
    page.get_by_role("textbox", name="Merchant").fill("Merchant")
    page.get_by_role("button", name="Save").click()
    page.get_by_label("Show more").click()
    page.get_by_test_id("selection-list").get_by_text("Tag").click()
    page.get_by_label("1 :").click()
    page.get_by_role("button", name="Submit ").click()
    page.get_by_label("Create").click()
    try:
        page.get_by_text("Create expense").click()
    except:
        page.get_by_text("Submit expense").nth(1).click()
    page.get_by_placeholder("0").fill("50")
    page.locator("#numPadContainerView").get_by_role("button", name="Next").click()
    page.get_by_label("Show more").click()
    page.get_by_test_id("selection-list").get_by_text("Tag").click()
    page.get_by_label("1 :").click()
    page.get_by_test_id("selection-list").get_by_text("Merchant").click()
    page.get_by_role("textbox", name="Merchant").fill("Merchant7077")
    page.get_by_role("button", name="Save").click()
    page.get_by_role("button", name="Submit ").click()
    page.get_by_label("View details").click()
    page.get_by_text("1 :").nth(2).click()
    page.get_by_text("Tag").nth(1).click()
    locator = page.locator("div.css-text-146c3p1", has_text="huigigjggiigkbbjhj").last

    word_break = locator.evaluate(
        """(node) => window.getComputedStyle(node).getPropertyValue("word-break")"""
    ).strip()
    
    assert word_break == "break-all", "Tag name truncated"
    
def test_run(membera_first_name="Sai", membera_last_name="Yagna"):
    with sync_playwright() as p:
        browser_membera, page_membera, user_email2 = login_member_a(p, membera_first_name, membera_last_name)
        check_color(page_membera)



        
        browser_membera.close()

if __name__ == "__main__":
    test_run()
