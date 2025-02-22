import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
from playwright.sync_api import sync_playwright, expect
import time 

from utils.trace_cleaner import trace_cleaner

static_email = "totherandomuser+40121580@gmail.com"

def login(p, if_phone=False, first_name="John", last_name="Cena"):

    browser = p.chromium.launch(headless=True, slow_mo=1000, args=["--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"])

    if if_phone:
        phone = p.devices['iPhone 12 Pro']
        context = browser.new_context(**phone)
    else:
        context = browser.new_context()

    page = context.new_page()

    page.goto('https://dev.new.expensify.com:8082/') 

    phone_or_email_input = page.locator('input[type="email"]')
    expect(phone_or_email_input).to_be_visible()
    phone_or_email_input.fill(static_email)

    page.get_by_role("button", name="Continue").click()
    page.get_by_role("button", name="Join").click()
    page.get_by_role("button", name="Join").wait_for(state="hidden")
    
    expect(page.locator("text=What do you want to do today?")).to_be_visible(timeout=50000)

    try:

        page.locator("text='Track and budget expenses'").click()
        page.wait_for_timeout(1000)


        first_name_input = page.locator('input[name="fname"]')
        expect(first_name_input).to_be_visible()
        first_name_input.fill(first_name)  
        first_name_input = page.locator('input[name="lname"]')  
        expect(first_name_input).to_be_visible()
        first_name_input.fill(last_name)  


        continue_button = page.locator('button[data-tag="pressable"][tabindex="0"]', has_text="Continue")
        expect(continue_button).to_be_visible()
        continue_button.click()
    except:
        pass

    return browser, page


def test():
    with sync_playwright() as p:
        browser, page = login(p, True)
        context = page.context
        context.tracing.start(screenshots=True, snapshots=True)
        try:

            page.get_by_label("Back").last.click()
            page.get_by_label("Close").last.click()


            plus_icon = page.locator('button[aria-label="Start chat (Floating action)"]')
            expect(plus_icon).to_be_visible()
            plus_icon.click()


            new_workspace_button = page.locator('div[aria-label="New workspace"]')
            expect(new_workspace_button).to_be_visible()
            new_workspace_button.click()
            page.get_by_text("Members").click()
            page.get_by_role("button", name="Invite member").click()
            page.get_by_test_id("selection-list-text-input").click()
            page.get_by_test_id("selection-list-text-input").fill("totherandomuser@gmail.com")
            page.wait_for_timeout(2000)
            page.get_by_text("totherandomuser@gmail.com").last.click()
            page.get_by_role("button", name="Next").click()
            page.get_by_test_id("WorkspaceInviteMessagePage").get_by_role("button", name="Invite").click()
            page.get_by_test_id("WorkspaceMembersPage").get_by_label("Back").last.click()
            page.get_by_label("Back").last.click()
            page.wait_for_timeout(1000)
            page.get_by_label("Back").last.click()
            page.wait_for_timeout(1000)
            page.get_by_label("Inbox").click()
            page.wait_for_timeout(1000)


            user_chat = page.locator('button[aria-label="Navigates to a chat"]', has_text="Deepak Dhaka").last
            expect(user_chat).to_be_visible(timeout=5000)
            user_chat.click()


            page.get_by_label("Create").click()
            page.get_by_text("Assign task").click()
            page.get_by_role("textbox", name="Title").click()
            page.get_by_role("textbox", name="Title").fill("task1")
            page.wait_for_timeout(1000)
            page.get_by_role("button", name="Next").click()
            page.get_by_role("button", name="Confirm task").click()
            page.wait_for_timeout(1000)


            page.get_by_role("button", name="Task").last.click()
            page.wait_for_timeout(1000)
            task_container = page.locator('div[data-testid="DisplayNamesWithTooltip"]', has_text="task1")
            expect(task_container).to_be_visible(timeout=5000)
            task_container.click()

            page.locator('[data-selection-scrapper-hidden-element="false"]', has_text="Delete").click()
            page.locator('button[data-tag="pressable"]', has_text="Delete").click()

            delete_detected = False
            count_f = 0
            for _ in range(50):  # Try up to 50 times

                count = page.locator('[data-testid="DisplayNamesWithTooltip"]', has_text="[Deleted task]").count()
                if count > 0:
                    print(f"Detected '[Deleted task]' {count} time(s) in page content!")
                    count_f += count
                    delete_detected = True
                page.wait_for_timeout(10)

            if not delete_detected:
                print("Delete text was not detected after retries.")

            assert count_f == 0, "[Deleted task] text has been found, It should not be there ideally!!"
        except Exception as e:
            print("Test failed with exception:", e)
            raise
        finally:
            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
