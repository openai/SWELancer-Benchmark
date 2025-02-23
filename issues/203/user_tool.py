import sys, os
from utils.trace_cleaner import trace_cleaner

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
from playwright.sync_api import sync_playwright, expect

site_url = "https://dev.new.expensify.com:8082/"
primary_email = "sujildevkota@gmail.com"


def generate_random_email():
    timestamp = int(time.time())
    return f"{primary_email.split('@')[0]}+{timestamp}@{primary_email.split('@')[1]}"


def create_new_account_and_login(page, first_name, last_name):
    user_email = generate_random_email()
    page.goto(site_url)


    phone_or_email_input = page.locator('input[type="email"]')
    expect(phone_or_email_input).to_be_visible()
    phone_or_email_input.fill(user_email)
    page.wait_for_timeout(1000)


    continue_button = page.locator('button[tabindex="0"]')
    expect(continue_button).to_be_visible()
    continue_button.click()
    page.wait_for_timeout(1000)


    try:
        print("Clicking the join button again if needed")
        expect(continue_button).to_be_visible()
        continue_button.click()
    except Exception as e:
        pass


    page.locator("text='Track and budget expenses'").click()
    page.wait_for_timeout(1000)
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()
    page.wait_for_timeout(1000)

    return user_email


def test_workspace_settings():
    first_name = "Sujil"
    last_name = "Devkota"

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True, slow_mo=500, args=[
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ])
        
        context1 = browser.new_context()
        context2 = browser.new_context()
        

        context1.tracing.start(title="trace1", screenshots=True, snapshots=True)
        context2.tracing.start(title="trace2", screenshots=True, snapshots=True)
        trace_path1 = "/app/expensify/user_tool/output_browser1.zip"
        trace_path2 = "/app/expensify/user_tool/output_browser2.zip"

        try:
            page1 = context1.new_page()
            user1_email = create_new_account_and_login(page1, first_name + "1", last_name + "1")

            page2 = context2.new_page()
            user2_email = create_new_account_and_login(page2, first_name + "2", last_name + "2")


            plus_button = page2.locator('button[aria-label="Start chat (Floating action)"]')
            expect(plus_button).to_be_visible()
            plus_button.click()
            page2.wait_for_timeout(1000)

            new_workspace_option = page2.locator('div[aria-label="New workspace"]')
            expect(new_workspace_option).to_be_visible()
            new_workspace_option.click()
            page2.wait_for_timeout(1000)

            more_features_option = page2.locator('div[aria-label="Members"]')
            expect(more_features_option).to_be_visible()
            more_features_option.click()

            invite_member_button = page2.locator('button:has(div:has-text("Invite member"))').last
            expect(invite_member_button).to_be_visible()
            invite_member_button.click()

            email_input = page2.locator('input[aria-label="Name, email, or phone number"]')
            expect(email_input).to_be_visible()
            email_input.fill("sujildevkota+1733384438@gmail.com")
            page2.wait_for_timeout(1000)

            user_email_option = page2.locator(f'button[aria-label="{first_name + "1" + " " + last_name + "1"}"] div:has-text("sujildevkota+1733384438@gmail.com")').last
            expect(user_email_option).to_be_visible()
            user_email_option.click()
            page2.wait_for_timeout(1000)
            page2.keyboard.press("Enter")

            invite_button = page2.locator('button:has(div)').get_by_text("Invite", exact=True)
            expect(invite_button).to_be_visible()
            invite_button.click()
            page2.wait_for_timeout(1000)

            workspace_setting_url = page2.url
            page1.goto(workspace_setting_url)
            page1.wait_for_timeout(5000)

            more_features_menu = page1.locator('div[aria-label="More features"]')
            categories_menu = page1.locator('div[aria-label="Categories"]')

            assert more_features_menu.count() == 0, "More features menu should not be visible for user1"
            assert categories_menu.count() == 0, "Categories menu should not be visible for user1"

        except Exception as e:

            raise e
        finally:

            context1.tracing.stop(path=trace_path1)
            trace_cleaner(trace_path1)

            context2.tracing.stop(path=trace_path2)
            trace_cleaner(trace_path2)

            browser.close()
