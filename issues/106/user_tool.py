from playwright.sync_api import sync_playwright, expect
from utils.trace_cleaner import trace_cleaner

user_email = "totherandomuser+52642@gmail.com"

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

            page.get_by_label("My settings").click()
            page.get_by_label("Subscription").click()
            page.get_by_role("button", name="Add payment card").click()
            page.get_by_role("textbox", name="Card number").click()
            page.get_by_role("textbox", name="Card number").fill("4111 1111 1111 1111")
            page.get_by_role("textbox", name="Name on card").click()
            page.get_by_role("textbox", name="Name on card").fill("Test Test")
            page.get_by_role("textbox", name="Expiration date").click()
            page.get_by_placeholder("MMYY").fill("1228")
            page.get_by_role("textbox", name="CVV").click()
            page.get_by_role("textbox", name="CVV").fill("564")
            try:
                page.get_by_role("textbox", name="Zip code").click()
                page.get_by_role("textbox", name="Zip code").fill("EH1 1BB")
            except:
                page.get_by_role("textbox", name="Zip / Postcode").click()
                page.get_by_role("textbox", name="Zip / Postcode").fill("EH1 1BB")

            page.get_by_text("Currency").click()
            page.get_by_test_id("selection-list").get_by_label("GBP").click()
            page.get_by_label("I accept the Expensify Terms").click()
            page.get_by_test_id("AddPaymentCard").get_by_role("button", name="Add payment card").click()

            expect(page.get_by_text("Please enter a valid zip code.")).not_to_be_visible()
        finally:
            # Stop tracing and export the trace file
            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            context.tracing.stop(path=trace_path)
            trace_cleaner(trace_path)
            browser.close()


# For running the test directly, you can uncomment the following line:
# test()
