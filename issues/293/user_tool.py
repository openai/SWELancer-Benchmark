import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from playwright._impl._page import Page
from utils.trace_cleaner import trace_cleaner


def launch_browser(playwright, platform="desktop"):
    mobile_context = {}

    if platform.lower() == "mobile":
        mobile_context = {
            "viewport": {"width": 540, "height": 864},
            "is_mobile": True,
        }

    browser = playwright.chromium.launch(headless=True, args=[
        "--ignore-certificate-errors",
        "--disable-web-security",
        "--disable-features=IsolateOrigins,site-per-process"
    ])
    context = browser.new_context(**mobile_context)
    context.tracing.start(screenshots=True, snapshots=True, sources=True)
    page = context.new_page()

    return browser, context, page


def login_user_if_not_logged_in(page: Page, platform="desktop"):
    page.bring_to_front()

    page.goto("https://dev.new.expensify.com:8082/")

    email = "freelancer.test.exp+17334747386155@gmail.com"

    page.locator('input[type="email"]').fill(email)
    page.locator("button", has_text="Continue").click()
    page.wait_for_timeout(3000)
    page.get_by_test_id("validateCode").fill("123456")


def verify_receipt_violation_error_message(page: Page, member_name: str, approval_required_amount: int):
    page.get_by_label("Navigates to a chat").get_by_text(member_name, exact=True).click()
    page_id = page.url.rstrip("/").split("/")[-1]
    page.get_by_test_id(f"report-screen-{page_id}").get_by_role(
        "button", name="View details"
    ).first.click()

    page.wait_for_timeout(5000)

    expect(
        page.get_by_text("Expense exceeds auto approval limit of undefined"),
        "The approval limit should not be undefined",
    ).to_have_count(0)

    approval_error_message = (page.get_by_text(f"Expense exceeds auto approval limit of ${approval_required_amount}")
                              if page.get_by_text(f"Expense exceeds auto approval limit of ${approval_required_amount}").is_visible()
                              else page.get_by_text(f"Expense exceeds auto approval limit of ${approval_required_amount}").nth(1))
    
    expect(approval_error_message, "The approval limit should be correct").to_have_count(1)


def test_receipt_violation_should_show_correct_error_message():
    playwright = sync_playwright().start()
    browser, context, page = launch_browser(playwright)
    try:
        login_user_if_not_logged_in(page)
        page.wait_for_timeout(2000)
        verify_receipt_violation_error_message(page, "Asaad J", 100)
    finally:
        context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
        trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
        browser.close()
        playwright.stop()


test_receipt_violation_should_show_correct_error_message()
