import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import Page, expect, sync_playwright

SITE_URL = "https://dev.new.expensify.com:8082/"
PRIMARY_EMAIL = "expensifyolddot+1732950525@gmail.com"
FIRST_NAME = "expensifyolddot"
LAST_NAME = "1732950525"

def create_user(
    page: Page, firstname: str, lastname: str
):

    page.get_by_test_id("username").fill(PRIMARY_EMAIL)
    page.wait_for_timeout(1000)
    page.get_by_role("button", name="Continue").click()
    page.wait_for_timeout(1000)
    page.get_by_role("button", name="Join").click()


    if page.get_by_text("Track and budget expenses").is_visible():
        page.get_by_text("Track and budget expenses").click()
        page.get_by_role("textbox", name="First name").fill(firstname)
        page.get_by_role("textbox", name="Last name").fill(lastname)
        page.wait_for_timeout(1000)
        page.get_by_role("button", name="Continue").click()


def close_button_if_present(page: Page):
    """
    Occasionally, there is a close button that prevents any clicks on the page as
    it covers most of the screen. This button cannot be seen visually.
    """
    close_button = page.locator('button[aria-label="Close"]')
    if close_button.is_visible():
        close_button.click()


def test_error_message():

    with sync_playwright() as p:


        phone = p.devices["Galaxy S9+"]
        browser = p.chromium.launch(
            headless=True,
            proxy={'server': 'http://127.0.0.1:8080'},
            args=[
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
            ],
        )
        context = browser.new_context(**phone)
        page = context.new_page()

        page.goto(SITE_URL)


        create_user(page, FIRST_NAME, LAST_NAME)
        page.wait_for_timeout(1000)


        close_button_if_present(page)
        page.get_by_label("My settings").click()
        page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()
        page.get_by_label("New workspace").first.click()
        page.get_by_label("Back").last.click()
        page.get_by_label("Back").last.click()


        close_button_if_present(page)
        page.get_by_label("My settings").click()
        page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()
        page.get_by_label("row").click()
        page.get_by_label("More features").click()
        page.get_by_label("Document and reclaim eligible").click()
        page.wait_for_timeout(2000)


        page.get_by_label("Taxes").click()
        page.get_by_role("button", name="Add rate").click()
        page.get_by_role("menuitem", name="Name Required").click()
        page.get_by_role("textbox", name="Name").fill("<h>")
        page.get_by_test_id("TextSelectorModal").get_by_role(
            "button", name="Save"
        ).click()


        expect(page.get_by_text("Invalid character")).to_be_visible()


        context.close()
        browser.close()