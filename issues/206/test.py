import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)


import re
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page


def generate_random_email():
    return "turingtemp+67867@gmail.com"


def login_user(p: PlaywrightContextManager, first_name="Ayush", last_name="G") -> tuple[Browser, Page, str]:

    browser = p.chromium.launch(
        channel="chrome",
        headless=True,
        slow_mo=800,
        args=[
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ]
    )
    page = browser.new_page()
    user_email = generate_random_email()


    page.goto('https://dev.new.expensify.com:8082/') 


    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()


    try: 
        page.locator('button[tabindex="0"]').click() 
    except Exception:
        print("Join button not found")

        

    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()
    

    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()
    
    return browser, page, user_email



def test_save_description_in_submitted_expense():
    with sync_playwright() as p:

        browser, page, user_email = login_user(p)


        page.get_by_label("My settings").click()
        page.get_by_text("Contact method").click()
        page.get_by_role("button", name="New contact method").click()
        page.get_by_role("textbox", name="Email/Phone number").fill("turingtemp+89116@gmail.com")
        page.get_by_role("button", name="Add").click()


        page.get_by_test_id("ValidateCodeActionModal").get_by_role("textbox").fill("124435")

        
        try:
            page.locator("div").filter(has_text=re.compile(r"^Verify$")).nth(1).click()
        except:
            print("Verification modal not found")
        page.locator('button[aria-label="Back"][type="button"][role="button"][data-tag="pressable"]').nth(-1).click()
        page.get_by_text("Sign out").click()
        page.get_by_test_id("username").fill("turingtemp+89117@gmail.com")
        page.get_by_role("button", name="Continue").click()
        page.get_by_role("button", name="Unlink").click()
        page.get_by_test_id("web_picker").select_option("es")
        spanish_link_sent = page.get_by_text("¡Enlace enviado!")
        expect(spanish_link_sent).to_be_visible()

        browser.close()
