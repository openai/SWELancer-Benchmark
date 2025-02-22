import re
import time

from playwright.sync_api import Page, expect, sync_playwright


# Utility to generate a random email
def generate_email():
    return f"turingtemp+1739814086@gmail.com"


def create_user(
    page: Page, firstname: str, lastname: str = None, timestamp: int = None
):
    # Sign up
    page.get_by_test_id("username").fill(generate_email())
    page.get_by_role("button", name="Continue").click()
    page.get_by_role("button", name="Join").click()

    # Update profile
    page.get_by_text("Track and budget expenses").click()
    page.get_by_role("textbox", name="First name").fill(firstname)
    page.get_by_role("textbox", name="Last name").fill(lastname)
    page.get_by_role("button", name="Continue").click()


def test_issue():

    with sync_playwright() as p:

        # Launch chromium and open new page
        browser = p.chromium.launch(headless=False, slow_mo=500, args=[ "--disable-web-security", "--disable-features=IsolateOrigins, site-per-process"])
        context = browser.new_context(**p.devices["Pixel 5"])
        page = context.new_page()

        page.goto("https://dev.new.expensify.com:8082/")

        try:
            create_user(page, "TestUser", "Surname")
        except:
            pass

        page.locator('span:text("TestUser Surname (you)")').click()
        page.get_by_role("button", name="Create").click()
        page.get_by_label("Assign task").click()
        page.get_by_role("textbox", name="Title").fill("title1")
        page.get_by_role("textbox", name="Title").press("Tab")
        page.get_by_role("textbox", name="Description (optional)").fill("desc1")
        page.get_by_role("button", name="Next").click()
        page.get_by_role("button", name="Confirm task").click()
        page.get_by_role("button", name="Task").first.click()
        page.get_by_role("button", name="Mark as complete").click()

        # header = page.locator("div:has(> div:has(> div:has(> button[aria-label='Back'])))")
        header = page.locator("div:has(div:has(div:has(button[aria-label='Back'])))").last

        # Ensure the element exists before checking its border
        assert header.count() > 0, "Test Failed: Header div not found!"

        # Get the computed style for border-bottom
        border_bottom = header.evaluate("element => window.getComputedStyle(element).borderBottomWidth")

        assert border_bottom != "0px", "Test Failed: Bottom border is missing!"

        # ---------------------
        context.close()
        browser.close()


