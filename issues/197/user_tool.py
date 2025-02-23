import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page
from utils.trace_cleaner import trace_cleaner

onboarding = False


def generate_random_email():
    task_number = "19398"
    return f"jellystarfish99+{task_number}@gmail.com"


def login_user(p: PlaywrightContextManager, first_name="Milan", last_name="T") -> tuple[Browser, Page, str]:

    browser = p.chromium.launch(headless=True, args=["--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"])
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

    if page.locator("text=What do you want to do today?").is_visible():
        global onboarding
        onboarding = True

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

        page.context.tracing.start(screenshots=True, snapshots=True, sources=True)

        try:
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
            message.last.click(button="right")
            page.wait_for_timeout(1000)

            pos_before = page.get_by_text("1 Reply").last.bounding_box()['x']

            edit_comment = page.get_by_text(f"Edit comment")
            expect(edit_comment).to_be_visible()
            edit_comment.click()
            page.wait_for_timeout(1000)

            pos_after = page.get_by_text("1 Reply").last.bounding_box()['x']

            assert pos_before == pos_after

        except Exception as e:
            print(f"Test encountered an error: {e}")
            raise

        finally:

            page.context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            browser.close()
