import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import os
from PIL import Image
from playwright.sync_api import Page, sync_playwright
from utils.trace_cleaner import trace_cleaner


def get_pixel_colour(image_path):
    """Open image and return the RGB value of the first pixel."""
    img = Image.open(image_path)
    return img.getpixel((100, 100))  # Get the RGB value of the pixel at (100, 100)


def take_and_compare_screenshots(page, iteration):
    """Take screenshots, compare first pixel, and delete the screenshots, then click overlay button."""
    # Set screenshot file names with iteration to avoid overwriting
    screenshot_before = f"screenshot_before_{iteration}.png"
    screenshot_after = f"screenshot_after_{iteration}.png"

    # Take a screenshot before an action
    page.screenshot(path=screenshot_before, full_page=True)

    # Perform the action (click Equipment)
    page.get_by_label("Equipment").click()

    # Take a screenshot after the action
    page.screenshot(path=screenshot_after, full_page=True)

    # Compare the first pixel of both screenshots
    pixel_before = get_pixel_colour(screenshot_before)
    pixel_after = get_pixel_colour(screenshot_after)

    # Assert that the first pixel is exactly the same to ensure no blinking observed
    assert pixel_before == pixel_after, f"Iteration {iteration}: The first pixel of both images is not the same! Blinking Observed"

    # Delete screenshots after the comparison
    os.remove(screenshot_before)
    os.remove(screenshot_after)

    # Click the overlay bottom button to continue the flow
    page.locator("#overLayBottomButton").click()


# Utility to generate a random email
def generate_random_email(timestamp: str):
    return f"testuser+{timestamp}@gmail.com"


def create_user(
    page: Page, firstname: str, lastname: str = None, timestamp: int = None
):
    timestamp = timestamp
    # Sign up
    page.get_by_test_id("username").fill(generate_random_email(timestamp))
    page.get_by_role("button", name="Continue").click()
    page.get_by_role("button", name="Join").click()

    try:
        # Update profile
        page.get_by_text("Track and budget expenses").click()
        page.get_by_role("textbox", name="First name").fill(f"testuser+{timestamp}@gmail.com")
        page.wait_for_timeout(1000)
        page.get_by_role("button", name="Continue").click()
    except:
        pass


def close_button_if_present(page: Page):
    """
    Occasionally, there is a close button that prevents any clicks on the page as
    it covers most of the screen. This button cannot be seen visually.
    """
    close_button = page.locator('button[aria-label="Close"]')
    if close_button.is_visible():
        close_button.click()


def task_check(page):
    page.get_by_label("My settings").click()
    page.get_by_label("Preferences").click()
    page.get_by_label("Use device settings").click()
    page.get_by_label("Dark").click()
    page.get_by_label("Inbox").click()
    page.get_by_role("button", name="Navigates to a chat").get_by_text(
        "testuser+10010022@gmail.com (you)", exact=True
    ).click()
    page.get_by_label("Create").last.click()
    page.wait_for_timeout(2000)
    page.get_by_label("Track expense").click()
    page.get_by_label("Manual").click()
    page.get_by_placeholder("0").fill("200")
    page.locator("#numPadContainerView").get_by_role("button", name="Next").click()
    page.get_by_role("button", name="Track expense").click()

    # Call the take_and_compare_screenshots function 5 times
    for i in range(1, 6):
        page.get_by_role("button", name="Categorize it").click()
        take_and_compare_screenshots(page, i)


def test_expensify_0000():
    with sync_playwright() as p:
        timestamp = 10010022

        browser = p.chromium.launch(headless=True, slow_mo=1000, args=[
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
        ])
        context = browser.new_context()

        # Start tracing
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        try:
            page = context.new_page()
            page.goto("https://dev.new.expensify.com:8082/")

            # Create user
            create_user(page, "TestUser", f"{timestamp}", timestamp)
            close_button_if_present(page)
            task_check(page)
        except Exception as e:
            raise e
        finally:
            # Stop tracing and save the trace
            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            browser.close()
