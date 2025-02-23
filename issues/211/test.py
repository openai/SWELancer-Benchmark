import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page


def generate_random_email():
    return f"testerbro7077+879478@gmail.com"


def login_user(p: PlaywrightContextManager, first_name="Milan", last_name="T") -> tuple[Browser, Page, str]:

    browser = p.chromium.launch(channel="chrome", headless=True, slow_mo = 500, args=[
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
    ])
    page = browser.new_page()
    user_email = generate_random_email()


    page.goto('https://dev.new.expensify.com:8082/') 


    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(1000)


    try: 
        page.locator('button[tabindex="0"]').click() 
        page.wait_for_timeout(1000)
    except Exception:
        pass

    expect(page.locator("text=What do you want to do today?")).to_be_visible()
        

    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()
    page.wait_for_timeout(1000)


    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()
    page.wait_for_timeout(1000)

    return browser, page, user_email


def test_add_reaction_to_chat_message_with_tab_key():
    with sync_playwright() as p:

        browser, page, user_email = login_user(p)

        personal_chat = page.get_by_text(f"Milan T (you)").nth(0)
        expect(personal_chat).to_be_visible()
        personal_chat.click()

        create = page.locator('button[aria-label="Create"]').nth(1)
        expect(create).to_be_visible()
        create.click()

        task = page.get_by_text("Assign task").nth(0)
        expect(task).to_be_visible()
        task.click()
        page.wait_for_timeout(1000)

        page.locator('input[aria-label="Title"]').nth(0).fill("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")

        next_button = page.locator('button', has_text="Next").nth(0)
        expect(next_button).to_be_visible()
        next_button.click()

        length_warning = page.get_by_text("Character limit exceeded").nth(0)
        expect(length_warning).to_be_visible()

        page.wait_for_timeout(2000)

        browser.close()