import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time

from playwright.sync_api import Page, expect, sync_playwright, Locator


# Utility to generate a random email
def generate_random_email(timestamp: int = int(time.time())):
    return f"testerbro7077+7832526@gmail.com"


def create_user(
    page: Page, firstname: str, lastname: str = None, timestamp: int = None
):

    # Sign up
    page.get_by_test_id("username").fill(generate_random_email())
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


def close_button_if_present(page: Page):
    """
    Occasionally, there is a close button that prevents any clicks on the page as
    it covers most of the screen. This button cannot be seen visually.
    """
    close_button = page.locator('button[aria-label="Close"]')
    if close_button.is_visible():
        close_button.click()


def is_element_visible_in_viewport(page: Page, elem: Locator):

    # Get the bounding box of the element
    bounding_box = elem.bounding_box()

    if bounding_box:
        x, y, width, height = (
            bounding_box["x"],
            bounding_box["y"],
            bounding_box["width"],
            bounding_box["height"],
        )
        viewport_size = page.viewport_size
        viewport_width = viewport_size["width"]
        viewport_height = viewport_size["height"]

        # Check if the element is within the viewport bounds
        if (
            x + width > 0
            and x < viewport_width
            and y + height > 0
            and y < viewport_height
        ):
            return True
        else:
            return False
    else:
        return False


def test_menu_item():

    with sync_playwright() as p:
        timestamp = int(time.time())

        # Launch chromium and open new page
        browser = p.chromium.launch(channel="chrome", headless=True, args=[
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ])
        context = browser.new_context()
        page = context.new_page()

        page.goto("https://dev.new.expensify.com:8082/")

        # create user
        create_user(page, "TestUser", "me")
        page.wait_for_timeout(1000)

        # Assign Task to user
        long_email = (
            "testuser8PvDmrZ4gE2zDyRNFUYJf1u5i3N3tscMk3Jv4lhsk03vYEYQsGIw@gmail.com"
        )
        close_button_if_present(page)
        page.get_by_text("TestUser me (you)").click()
        page.get_by_label("Create").last.click()
        page.get_by_label("Assign task").click()
        page.get_by_role("textbox", name="Title").fill("Title")
        page.get_by_role("textbox", name="Description (optional)").fill("Desc")
        page.keyboard.press("Enter")
        page.get_by_role("menuitem", name="Assignee").click()
        page.get_by_test_id("selection-list-text-input").fill(long_email)
        page.get_by_label(long_email).click()

        elem = page.get_by_label(long_email).get_by_role("img").nth(1)

        assert (
            is_element_visible_in_viewport(page, elem) == True
        ), "Element is not visible in viewport"

        # ---------------------
        context.close()
        browser.close()