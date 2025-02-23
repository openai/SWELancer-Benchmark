import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import re
import time
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page

def login_user(p: PlaywrightContextManager, first_name="Ayush", last_name="G") -> tuple[Browser, Page, str]:

    browser = p.chromium.launch(headless=True, args=["--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"], proxy={"server": "http://localhost:8080"})
    page = browser.new_page()


    page.goto('https://dev.new.expensify.com:8082/') 


    page.locator('input[type="email"]').fill("checkissue+19022@gmail.com")
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(2000) 


    try: 
        page.locator('button[tabindex="0"]').click() 
        page.wait_for_timeout(5000) 
    except Exception:
        pass
    
    if page.locator("text=What do you want to do today?").is_visible():
        page.wait_for_timeout(1000)

        page.locator("text='Track and budget expenses'").click()
        page.get_by_role("button", name="Continue").click()
        page.wait_for_timeout(1000) 


        page.locator('input[name="fname"]').fill(first_name)
        page.locator('input[name="lname"]').fill(last_name)
        page.get_by_role("button", name="Continue").last.click()
        page.wait_for_timeout(1000)

    return browser, page


def test_save_description_in_submitted_expense():
    with sync_playwright() as p:

        browser, page = login_user(p)

        page.locator('span:text("Ayush G (you)")').click()

        plus_create_icon = page.locator('button[aria-label="Create"]').last
        expect(plus_create_icon).to_be_visible()
        plus_create_icon.click()

        page.get_by_text("Assign task").click()
        page.wait_for_timeout(2000) 
        page.get_by_role("textbox", name="Title").fill("title1")
        page.get_by_role("textbox", name="Title").press("Tab")
        page.get_by_role("textbox", name="Description (optional)").fill("description1")
        page.get_by_role("button", name="Next").click()

        page.locator('button div:text("Confirm task")').click()
        page.wait_for_timeout(1000) 

        task_title_div = page.locator('div[data-testid="comment"] div:has-text("title1")')
        task_title_div.click()
        
        expanded_task_title_div = page.locator('div[aria-label="description1"]').first
        expanded_task_title_div.click()
        page.wait_for_timeout(1000) 



        page.keyboard.press('Backspace')        
        page.keyboard.press('Backspace')
        page.keyboard.press('Backspace')
        page.keyboard.press('Backspace')
        page.keyboard.press('Backspace')
        page.keyboard.press('Backspace')
        page.keyboard.press('Backspace')
        page.keyboard.press('Backspace')
        page.keyboard.press('Backspace')
        page.keyboard.press('Backspace')
        page.keyboard.press('Backspace')
        page.keyboard.press('Backspace')
        page.keyboard.press('Backspace')

        page.wait_for_timeout(1000)

        page.get_by_role("button", name="Save").click()
        page.wait_for_timeout(2000)

        field_required_warning = page.locator('div:text("This field is required.")')
        expect(field_required_warning).to_be_hidden()

        browser.close()

