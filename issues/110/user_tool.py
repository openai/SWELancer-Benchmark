import imaplib
import email
import re
from playwright.sync_api import sync_playwright, expect, Page
from utils.trace_cleaner import trace_cleaner

EMAIL = "velmoner+479@gmail.com"
PASSWORD = "aory ezrb qkmi qkas"
NEWDOT_URL = "https://dev.new.expensify.com:8082/"


def user_login(page: Page, email_id: str, password: str):
    page.goto(NEWDOT_URL)

    page.locator('input[type="email"]').fill(email_id)
    page.wait_for_timeout(2000)
    page.get_by_role("button", name="Continue").nth(0).click()
    otp = "123456"
    page.wait_for_timeout(10000)
    page.locator('input[data-testid="validateCode"]').fill(otp)
    try:
        page.get_by_role("button", name="Sign In").click()
    except Exception as err:
        pass


def test_payment_text():
    with sync_playwright() as p:
        browser = p.chromium.launch(proxy={"server": "http://localhost:8080"}, headless=False, args=["--no-sandbox", "--disable-dev-shm-usage", "--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"], slow_mo=1000, channel="chromium")
        page = browser.new_page()
        # Get the context from the page to start tracing
        context = page.context
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        try:
            email1, dname1 = "velmoner+321@gmail.com", "fin land"
            email2, dname2 = "velmoner+8992@gmail.com", "gargi dime"

            user_login(page=page, email_id=EMAIL, password=PASSWORD)
            page.get_by_label("Start chat (Floating action)", exact=True).click()
            page.get_by_label("Start chat", exact=True).click()

            page.get_by_test_id("selection-list-text-input").fill(email1)
            page.get_by_label(dname1).get_by_role(
                "button", name="Add to group").click()

            page.get_by_test_id("selection-list-text-input").fill(email2)
            page.get_by_label(dname2).get_by_role(
                "button", name="Add to group").click()

            page.get_by_role("button", name="Next").click()
            page.get_by_role("button", name="Start group").click()

            chatroom_id = page.url.split("/")[-1]
            search_text = f"type:chat status:all in:{chatroom_id}"
            page.get_by_test_id(
                f"report-screen-{chatroom_id}").get_by_text("fin, gargi, wii").click()
            page.get_by_label("Leave").click()

            current_report_id = page.url.split("/")[-1]
            page.get_by_test_id(
                f"report-screen-{current_report_id}").get_by_label("Search").click()
            page.get_by_test_id("search-router-text-input").fill(search_text)
            page.wait_for_timeout(1500)
            page.get_by_label(search_text).click()
            page.wait_for_timeout(1000)
            page.get_by_text("Filters").click()
            page.get_by_test_id(
                "SearchAdvancedFiltersPage").get_by_text("In").click()

            empty_item_exists = False

            # condition to find
            for i in page.get_by_test_id("selection-list").get_by_role("button").all():
                if i.get_attribute("id") and i.get_attribute("id") == chatroom_id:
                    empty_item_exists = True
            assert not empty_item_exists, "Empty entry found in search list with green check"

        finally:
            output_zip = "/app/expensify/user_tool/output_browser1.zip"
            context.tracing.stop(path=output_zip)
            trace_cleaner(output_zip)
            browser.close()


# If running as main, execute the test
if __name__ == "__main__":
    test_payment_text()