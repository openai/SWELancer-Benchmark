from playwright.sync_api import sync_playwright, expect
from utils.trace_cleaner import trace_cleaner

user_email = "totherandomuser+53986@gmail.com"

def login(p, context):
    page = context.new_page()
    page.goto('https://dev.new.expensify.com:8082')

    # Step 1: Enter username and continue
    page.get_by_test_id("username").click()
    page.get_by_test_id("username").fill(user_email)
    page.get_by_role("button", name="Continue").click()

    # Step 2: Mark Inbox read and then get magic code from email
    magic_code = "123456"

    # Step 3: Fill in the magic code
    validate_code_input = page.locator('input[name="validateCode"]')
    expect(validate_code_input).to_be_visible()
    validate_code_input.fill(magic_code)
    page.wait_for_timeout(1000)

    return page


def test():
    with sync_playwright() as p:

        # Step 1: Main Browser Login
        browser = p.chromium.launch(headless=False, args=[
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ], slow_mo=500)

        context = browser.new_context()
        # Start tracing
        context.tracing.start(screenshots=True, snapshots=True, sources=True)

        try:
            page = login(p, context)
            
            page.get_by_test_id("CustomBottomTabNavigator").get_by_label("Search").click()
            page.wait_for_timeout(2000)
            page.get_by_role("button", name="Drafts").click()
            page.wait_for_timeout(2000)
            expect(page.get_by_role("button", name="View").nth(1)).to_be_visible()
            expect(page.get_by_role("button", name="View").nth(2)).to_be_visible()

        finally:
            # Stop tracing and export the trace file
            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            context.tracing.stop(path=trace_path)
            
            # Clean the trace file as needed
            trace_cleaner(trace_path)
            
            # Close the browser
            browser.close()


if __name__ == '__main__':
    test()