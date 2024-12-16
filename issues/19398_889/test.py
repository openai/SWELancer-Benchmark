import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page

onboarding = False

# Utility to generate a random email
def generate_random_email():
    task_number = "19398"
    return f"jellystarfish99+{task_number}@gmail.com"


def login_user(p: PlaywrightContextManager, first_name="Milan", last_name="T") -> tuple[Browser, Page, str]:
    # Launch chromiun and open new page
    browser = p.chromium.launch(headless=True, args=["--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"])
    page = browser.new_page()
    user_email = generate_random_email()

    # Step 1: Open expensify url
    page.goto('https://dev.new.expensify.com:8082/') 

    # Step 2: Enter email and click continue
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(1000)

    # Step 3: Click join button
    try: 
        page.locator('button[tabindex="0"]').click() 
        page.wait_for_timeout(1000)
    except Exception:
        pass

    if page.locator("text=What do you want to do today?").is_visible():
        onboarding = True
        # Step 4: Select 'Track and budget expenses' in onobarding page and click Continue
        page.locator("text='Track and budget expenses'").click()
        page.get_by_role("button", name="Continue").click()
        page.wait_for_timeout(1000)

        # Step 5: Enter first name, last name and click continue
        page.locator('input[name="fname"]').fill(first_name)
        page.locator('input[name="lname"]').fill(last_name)
        page.get_by_role("button", name="Continue").last.click()
        page.wait_for_timeout(1000)

    return browser, page, user_email


def test_add_reaction_to_chat_message_with_tab_key():
    with sync_playwright() as p:
        # Step 1: Login user 
        browser, page, user_email = login_user(p)

        if onboarding == True:
            personal_chat = page.get_by_text(f"Milan T (you)")
        else:    
            personal_chat = page.get_by_text(f"Jellystarfish99+19398@gmail.com (you)")

        expect(personal_chat).to_be_visible()
        personal_chat.click()
        page.wait_for_timeout(1000)
        
        page.get_by_role("textbox").fill("My Message")
        page.get_by_role("textbox").press("Enter")
        page.wait_for_timeout(1000)

        message = page.locator('span', has_text="My Message")
        expect(message).to_be_visible()
        message.click(button="right")
        page.wait_for_timeout(1000)

        reply_thread = page.get_by_text(f"Reply in thread")
        expect(reply_thread).to_be_visible()
        reply_thread.click()
        page.wait_for_timeout(1000)

        page.get_by_role("textbox").fill("My Reply")
        page.get_by_role("textbox").press("Enter")
        page.wait_for_timeout(1000)

        if onboarding == True:
            personal_chat = page.get_by_text(f"Milan T (you)").nth(0)
        else:    
            personal_chat = page.get_by_text(f"Jellystarfish99+19398@gmail.com (you)").nth(0)

        expect(personal_chat).to_be_visible()
        personal_chat.click()
        page.wait_for_timeout(1000)
        
        message = page.locator('.css-textHasAncestor-1jxf684', has_text='My Message')
        # expect(message).to_be_visible()
        message.last.click(button="right")
        page.wait_for_timeout(1000)

        pos_before = page.get_by_text("1 Reply").last.bounding_box()['x']

        edit_comment = page.get_by_text(f"Edit comment")
        expect(edit_comment).to_be_visible()
        edit_comment.click()
        page.wait_for_timeout(1000)

        pos_after = page.get_by_text("1 Reply").last.bounding_box()['x']

        assert pos_before == pos_after

        browser.close()
