import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time

from playwright.sync_api import Page, expect, sync_playwright



def generate_random_email():
    return f"testerbro7077+328769@gmail.com"


def create_user(
    page: Page, firstname: str, lastname: str = None, timestamp: int = None
):
    page.evaluate("""
        Onyx.merge('nvp_onboarding', { hasCompletedGuidedSetupFlow: false });
            """)

    page.reload()
    page.wait_for_timeout(1000)

    page.get_by_test_id("username").fill(generate_random_email())
    page.wait_for_timeout(1000)
    page.get_by_role("button", name="Continue").click()
    page.wait_for_timeout(1000)
    page.get_by_role("button", name="Join").click()
    page.wait_for_timeout(1000)
    


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


def test_composer_visibility():

    with sync_playwright() as p:


        browser = p.chromium.launch(channel="chrome", headless=True, args=[
             "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ])
        context = browser.new_context(viewport={"width": 375, "height": 667})
        page = context.new_page()

        page.goto("https://dev.new.expensify.com:8082/")


        create_user(page, "TestUser", "me")
        page.wait_for_timeout(1000)


        text = "Sample text"
        close_button_if_present(page)
        close_button_if_present(page)
        page.locator('button[aria-label="Navigates to a chat"]').nth(1).click()
        page.get_by_role("textbox").fill(text)
        page.keyboard.press("Enter")


        page.get_by_test_id("report-actions-list").get_by_text(text).click(
            button="right"
        )
        page.get_by_label("Edit comment").click()


        expect(page.get_by_label("Close")).to_be_visible()
        expect(page.get_by_label("Save changes")).to_be_visible()


        page.set_viewport_size({"width": 1280, "height": 720})
        page.wait_for_timeout(1000)  # Wait for the page to adjust


        page.get_by_label("Close").click()


        expect(page.get_by_label("Create")).to_be_visible()
        expect(page.get_by_role("textbox")).to_be_visible()
        expect(page.get_by_label("Send")).to_be_visible()


        context.close()
        browser.close()