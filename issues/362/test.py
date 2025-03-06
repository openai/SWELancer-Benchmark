import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page



def generate_random_email():
    return f"expensifyapp97+99999988@gmail.com"


def login_user(p: PlaywrightContextManager, first_name="Milan", last_name="T") -> tuple[Browser, Page, str]:


    proxy = {"server": "http://127.0.0.1:8080/"}
    args = ["--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"]
    browser = p.chromium.launch(headless=True, args=args, proxy=proxy)
    page = browser.new_page()
    user_email = generate_random_email()


    page.goto('https://dev.new.expensify.com:8082/') 


    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()
    time.sleep(1)


    try: 
        page.locator('button[tabindex="0"]').click() 
        time.sleep(1)
    except Exception:
        pass
    expect(page.locator("text=What do you want to do today?")).to_be_visible()
        

    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()
    time.sleep(1)


    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()
    time.sleep(1)

    return browser, page, user_email


def test_cursor_disabled():
    with sync_playwright() as p:

        browser, page, user_email = login_user(p)


        personal_chat = page.get_by_text(f"Milan T (you)")
        expect(personal_chat).to_be_visible()
        personal_chat.click()
        time.sleep(1)


        plus_create_icon = page.locator('button[aria-label="Create"]').last
        expect(plus_create_icon).to_be_visible()
        plus_create_icon.click()
        time.sleep(1)

        submit_expense_button = page.locator('div[aria-label="Assign task"]')
        expect(submit_expense_button).to_be_visible()
        submit_expense_button.click()
        time.sleep(1)

        page.get_by_role("textbox", name="Title").fill("Samuel")
        page.get_by_role("button", name="Next").click()
        page.get_by_role("button", name="Confirm task").click()
        page.get_by_role("checkbox", name="Task").click()


        page.locator('div[aria-label="Chat message"]').last.click()
        element = page.locator('text="Description"')
        element.click()


        cursor_style = element.evaluate("element => window.getComputedStyle(element).cursor")


        assert cursor_style == 'default', f"Expected cursor to be disabled, but it was '{cursor_style}'"

        print(f"Cursor style: {cursor_style}")


        browser.close()
