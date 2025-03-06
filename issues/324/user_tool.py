import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from playwright._impl._page import Page
from utils.trace_cleaner import trace_cleaner

SITE_URL = "https://dev.new.expensify.com:8082/"
PRIMARY_EMAIL = "expensifyolddot+1733831382@gmail.com"
FIRST_NAME = "Expenolddot"
LAST_NAME = "1733831382"


def login_user(
        page: Page, 
        first_name="Asaad", 
        last_name="I", 
        email: str = "testuser@gmail.com", 
        platform="chromium"
    ):



    page.goto(SITE_URL)


    page.locator('input[type="email"]').fill(email)
    page.locator('button', has_text="Continue").click()


    page.locator('button', has_text="Join").click()



    page.wait_for_timeout(2000)
    if page.locator("text='Track and budget expenses'").is_visible():
        page.locator("text='Track and budget expenses'").click()
        page.get_by_role("button", name="Continue").click()


        page.locator('input[name="fname"]').fill(first_name)
        page.locator('input[name="lname"]').fill(last_name)
        page.get_by_role("form").get_by_role("button", name="Continue").click()




    page.reload() # Need to reload for replaying the test
    if platform.lower() in ['ios', 'android']:
        page.get_by_label('Last chat message preview').filter(has_text='task for Track an expense').wait_for()
        page.get_by_label('Last chat message preview').filter(has_text='task for Track an expense').first.click()
    page.get_by_label("guided-setup-track-personal-").wait_for()

    if platform.lower() in ['ios', 'android']:
        page.get_by_label("Back").click()
        page.get_by_label("Inbox").wait_for()


def verify_go_back_works_after_reload_on_flag_page(page: Page):

    page.goto('https://dev.new.expensify.com:8082/r/5624984165978443')
    page.wait_for_timeout(5000)


    page.get_by_label("Chat message", exact=True).first.click(button="right")
    page.get_by_label("Flag as offensive").click()


    page.get_by_text("Choose a reason for flagging").wait_for()


    page.get_by_test_id("FlagCommentPage").get_by_label("Back").click()
    expect(page.get_by_label("Chat message", exact=True).first).to_be_visible()


    page.get_by_label("Chat message", exact=True).first.click(button="right")
    page.get_by_label("Flag as offensive").click()


    page.get_by_text("Choose a reason for flagging").wait_for()
    

    page.reload()


    page.get_by_test_id("FlagCommentPage").get_by_label("Back").click()
    expect(page.get_by_label("Chat message", exact=True).first).to_be_visible()


def test_go_back_after_reload_on_flag_page():
    """
    Test to verify that the go back works after reload on flag page
    """
    with sync_playwright() as p:
        platform = "ios"


        browser = p.chromium.launch(
            headless=True,
            args=[
                "--ignore-certificate-errors",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process"
            ],
            proxy={"server": "http://localhost:8080"},
            slow_mo=500
        )

        device_config = p.devices['iPhone 14']
        context_args = { "timezone_id": "Asia/Kathmandu" }
        merged_context_args = {**device_config, **context_args}
        context = browser.new_context(**merged_context_args)


        context.tracing.start(
            title="test_go_back_after_reload_on_flag_page",
            screenshots=True,
            snapshots=True,
            sources=True
        )

        page = context.new_page()

        try:

            login_user(page, FIRST_NAME, LAST_NAME, PRIMARY_EMAIL, platform)


            verify_go_back_works_after_reload_on_flag_page(page)

        except Exception as e:

            raise e
        finally:

            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            context.tracing.stop(path=trace_path)
            trace_cleaner(trace_path)


            context.close()
            browser.close()
