import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page


def login_user(p: PlaywrightContextManager, first_name="Milan", last_name="T") -> tuple[Browser, Page]:

    browser = p.chromium.launch(
            channel="chrome",
            headless=True,
            args=[
                "--ignore-certificate-errors",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process"
            ],
            proxy={"server": "http://localhost:8080"},
            slow_mo=500
        )
    
    context = browser.new_context(timezone_id = "Asia/Karachi")
    page = context.new_page()
    user_email = "expensify624+1734167519@gmail.com"

    page.goto('https://dev.new.expensify.com:8082/') 

    page.get_by_test_id("username").fill(user_email)
    page.get_by_role("button", name="Continue").click()
    page.get_by_role("button", name="Join").click()

    try:
        expect(page.locator("text=What do you want to do today?")).to_be_visible()
        page.get_by_text("Track and budget expenses").click()
        page.get_by_role("button", name="Continue").click()
        page.get_by_role("textbox", name="First name").fill(first_name)
        page.get_by_role("textbox", name="Last name").fill(last_name)
        page.get_by_role("form").get_by_role("button", name="Continue").click()
    except:
        pass

    try:
        expect(page.get_by_role("dialog").get_by_text("Welcome to Expensify")).to_be_visible()
        page.get_by_role("button", name="Get Started").click()
    except:
        pass

    return browser, page


def test_save_description_in_submitted_expense():
    with sync_playwright() as p:

        browser, page = login_user(p)

        page.locator('button[aria-label="Start chat (Floating action)"]').click()
        page.locator('div[aria-label="New workspace"]').click()
        page.locator('div[aria-label="Members"]').click()
        page.locator('div:text("Invite member")').click()

        invitee_email_id = "expensify624+1734167537@gmail.com"
        page.locator('div[aria-label="Name, email, or phone number"] >> input').fill(invitee_email_id)
        page.locator(f'div:text("{invitee_email_id}")').nth(1).click()
        page.locator('div:text("Next")').click()
        page.locator('text="Invite"').click()

        page.locator('button[aria-label="Back"]').click()
        page.locator('button[aria-label="Inbox"]').click()

        try: 
            page.locator(f'button[aria-label="Navigates to a chat"] >> div:text-is("Chat Report")').click()
        except Exception:
            try: 
                page.locator(
                    f'button[aria-label="Navigates to a chat"] >> div:text-is("{invitee_email_id}")'
                    ).click()
            except Exception:
                pass        
        
        page.locator(f'button[aria-label="{invitee_email_id}"]').click()

        expect(page.locator('div:text-is("2")')).to_be_visible()

        browser.close()