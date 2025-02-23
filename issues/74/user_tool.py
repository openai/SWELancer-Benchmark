import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import Page, sync_playwright, expect
from requests import Request
from utils.email_handler import get_unique_derived_email
from utils.trace_cleaner import trace_cleaner



def complete_onboarding(page: Page, first_name: str='John', last_name: str='Doe'):
    expect(page.locator("text=What do you want to do today?")).to_be_visible()


    page.locator("text='Track and budget expenses'").click()


    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()


def login(page: Page, user_email: str):
    page.locator('input[type="email"]').fill(user_email)
    page.get_by_role("button", name="Continue").click()

    if page.get_by_test_id("validateCode").is_visible():
        otp_code = '123456'
        page.get_by_test_id("validateCode").fill(otp_code)
        page.get_by_role("button", name="Sign in").click()
        page.get_by_text("Please enter the magic code").wait_for(state="hidden")
    else:
        page.get_by_role("button", name="Join").click()
        page.get_by_role("button", name="Join").wait_for(state="hidden")


    page.get_by_label("Inbox").wait_for(state="visible")

def test_open_report_requests():
    with sync_playwright() as p:
        base_email = "namesomerandomemail@gmail.com"
        password = "fkto mqnl wkuw ecgx"
        first_name = "Test"
        last_name = "User"

        derived_email = get_unique_derived_email(base_email)
        derived_email = 'namesomerandomemail+1734001531@gmail.com'
        print(derived_email)


        browser = p.chromium.launch(headless=True, args=[
            "--ignore-certificate-errors",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ], proxy={"server": "http://localhost:8080"}, slow_mo=500)
        context = browser.new_context()
        context.tracing.start(screenshots=True, snapshots=True)
        page = context.new_page()

        try:
            page.goto("https://dev.new.expensify.com:8082/")


            login(page, derived_email)
            complete_onboarding(page, first_name=first_name, last_name=last_name)

            page.get_by_role("textbox").fill("A message")
            page.keyboard.press("Enter")
            page.get_by_test_id("report-actions-list").get_by_text("A message").nth(0).click(button="right")
            page.get_by_role("menuitem", name="Reply in thread").click()

            page.get_by_role("textbox").fill("A message in thread")
            page.keyboard.press("Enter")
            page.go_back()

            open_report_requests_count = 0

            def check_request_url(request: Request):
                """
                Check if request ends in /api/OpenReport?
                """
                if "/api/OpenReport" in request.url:
                    nonlocal open_report_requests_count
                    open_report_requests_count += 1

            page.on("request", check_request_url)
            page.get_by_label("1 Reply").click()

            assert open_report_requests_count == 1, "Open request not called exactly once"
        finally:

            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            context.close()
            browser.close()
