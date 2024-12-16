import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from playwright._impl._browser import Browser
from playwright._impl._page import Page

username_1 = "5648948"
username_2 = "564445"

# Utility to generate a random email
def generate_random_email(username):
    return f"rgulraiz2000+{username}@gmail.com"


def create_user(page: Page, username: str, firstname: str, lastname: str) -> None:
    # join user #1

    email = generate_random_email(username)
    page.get_by_test_id("username").fill(email)
    page.get_by_role("button", name="Continue").click()
    page.get_by_role("button", name="Join").click()

    # Update profile
    page.get_by_text("Track and budget expenses").click()
    page.get_by_role("textbox", name="First name").fill(firstname)
    page.get_by_role("textbox", name="Last name").fill(lastname)
    page.get_by_role("button", name="Continue").click()

    return email

def test_generic():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True, slow_mo=1000, args=[
        "--ignore-certificate-errors",
        "--disable-web-security",
        "--disable-features=IsolateOrigins,site-per-process"
        ])
        context_1 = browser.new_context()
        context_2 = browser.new_context()

        # create users
        page_1 = context_1.new_page()
        page_1.goto("https://dev.new.expensify.com:8082/")
        email_1 = create_user(page_1, username_1, "John", "Doe")

        page_2 = context_2.new_page()
        page_2.goto("https://dev.new.expensify.com:8082/")
        email_2 = create_user(page_2, username_2, "Jane", "Doe")


        fab = page_1.locator('button[aria-label="Start chat (Floating action)"]')
        expect(fab).to_be_visible()
        fab.click()
        

        chat = page_1.get_by_text("Start chat")
        expect(chat).to_be_visible()
        chat.click()
        

        fill = page_1.locator('input[aria-label="Name, email, or phone number"]').fill(email_2)
        
        page_1.get_by_text("Jane Doe").click()
        

        create = page_1.locator('button[aria-label="Create"]').nth(1)
        expect(create).to_be_visible()
        create.click()
        

        task = page_1.get_by_text("Assign task")
        expect(task).to_be_visible()
        task.click()
        

        page_1.locator('input[aria-label="Title"]').fill("Test")

        next_button = page_1.locator('button', has_text="Next")
        expect(next_button).to_be_visible()
        next_button.click()
        

        description_click = page_1.get_by_text("Description").nth(1)
        expect(description_click).to_be_visible()
        description_click.click()
        

        description_field = page_1.locator('div[aria-label="Description (optional)"]').nth(3)
        is_focused = description_field.evaluate("element => element === document.activeElement")

        assert is_focused

        

        browser.close()
