import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import os

from playwright.sync_api import Page, sync_playwright


# Utility to generate a random email
def generate_random_email():
    return f"rgulraiz2000+468654@gmail.com"


def create_user(
    page: Page, firstname: str, lastname: str = None, email = ""
):
    # Sign up
    page.get_by_test_id("username").fill(email)
    
    page.get_by_role("button", name="Continue").click()
    
    page.get_by_role("button", name="Join").click()


    page.get_by_text("Track and budget expenses").click()
    page.get_by_role("textbox", name="First name").fill(firstname)
    page.get_by_role("textbox", name="Last name").fill(lastname)
    
    page.get_by_role("button", name="Continue").click()


def close_button_if_present(page: Page):
    """
    Occasionally, there is a close button that prevents any clicks on the page as
    it covers most of the screen. This button cannot be seen visually.
    """
    close_button = page.locator('button[aria-label="Close"]').nth(0)
    if close_button.is_visible():
        close_button.click()


def test_tooltip_avatar():
    with sync_playwright() as p:
        email = generate_random_email()

        # Define the relative path to the text file
        script_dir = os.path.dirname(__file__)
        image_file_path = os.path.join(script_dir, "turing.jpeg")

        browser = p.chromium.launch(channel="chrome", headless=True, slow_mo=2100, args=[
            "--ignore-certificate-errors",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ])
        context = browser.new_context()
        page = context.new_page()

        page.goto("https://dev.new.expensify.com:8082/")

        # Create user
        first_name = "John"
        last_name = "K"
        create_user(page, first_name, last_name, email)
        

        # Send message to self
        close_button_if_present(page)

        page.locator('button[aria-label="Navigates to a chat"]').nth(1).click()
        page.get_by_role("textbox").fill("Hey")
        page.keyboard.press("Enter")

        context.set_offline(True)

        # Set User Name
        page.get_by_label("My settings").click()
        page.get_by_text("Display name").click()
        page.get_by_role("textbox", name="First name").click()
        page.get_by_role("textbox", name="First name").fill(first_name)
        page.get_by_role("textbox", name="Last name").click()
        page.get_by_role("textbox", name="Last name").fill(last_name)
        page.get_by_role("button", name="Save").click()
        page.get_by_label("Inbox").click()

        # Update profile photo
        page.get_by_label("My settings").click()
        with page.expect_file_chooser() as file_chooser_info:
            page.get_by_role("button", name="Edit photo").click()
        file_chooser = file_chooser_info.value
        file_chooser.set_files(image_file_path)
        print(f"Uploading file: {image_file_path}")

        page.get_by_role("button", name="Save").click()
        page.get_by_label("Inbox").click()
        

        # Verify avatar and tooltip
        page.get_by_text(f"{first_name} {last_name} (you)").nth(0).click()

        avatar = page.get_by_role("button", name=email).first
        img_src = avatar.locator("img").get_attribute("src")

        images_count_before = page.locator(f'img[src="{img_src}"]').count()

        avatar.hover()

        

        images_count_after = page.locator(f'img[src="{img_src}"]').count()

        assert (
            images_count_after == images_count_before + 1
        ), "Tooltip has different image from the avatar"

        context.close()
        browser.close()
