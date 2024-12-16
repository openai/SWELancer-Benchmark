import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from utils.trace_cleaner import trace_cleaner

USER_EMAIL = "xecuycismfsga+50419@gmail.com"
PASSWORD = "uwgb zzoc cofa kaaq"


def login(page, user_email: str, password: str):
    page.get_by_test_id("username").fill(user_email)
    page.get_by_role("button", name="Continue").click()
    page.wait_for_timeout(3000)
    page.get_by_role("textbox").fill("123456")
    expect(page.get_by_label("Inbox")).to_be_visible(timeout=30000)


def test_category_approvers():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=[
            '--ignore-certificate-errors',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
        ], slow_mo=500)
        context = browser.new_context(viewport={"width": 1280, "height": 620})

        # Start tracing
        context.tracing.start(
            title="test_category_approvers",
            screenshots=True,
            snapshots=True,
            sources=True
        )
        page = context.new_page()

        try:
            page.goto("https://dev.new.expensify.com:8082/", timeout=50000)
            login(page, USER_EMAIL, PASSWORD)
            page.get_by_test_id("CustomBottomTabNavigator").get_by_label("Search").click()
            page.get_by_role("button", name="Nov 26 DAC Test 50419 Test").click()

            page.locator("#composer").last.fill("Heya")
            page.locator("#composer").last.press("Enter")

            page.get_by_text("Category").last.click()
            text = page.locator('div[data-testid="selection-list"] button').first.inner_text()
            new_label = (
                "Advertising" if "Benefits" in text else "Benefits"
            ) 
            page.get_by_label(new_label).first.click()

            page.locator("#composer").last.fill("More text")
            page.locator("#composer").last.press("Enter")
            page.wait_for_timeout(1000)

            expect(page.get_by_text("Test 50419 (you)")).not_to_be_visible()
        except Exception as e:
            # Reraise to ensure any failures are not ignored
            raise e
        finally:
            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            # Stop tracing and save
            context.tracing.stop(path=trace_path)
            # Clean the trace
            trace_cleaner(trace_path)

            # Close the context and browser
            context.close()
            browser.close()
