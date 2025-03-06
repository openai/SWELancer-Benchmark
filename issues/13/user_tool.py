from playwright.sync_api import sync_playwright, expect
from utils.trace_cleaner import trace_cleaner

user_email = "testuserexpensify1@gmail.com"
password = ""
user_id = "testuserexpensify1+152@gmail.com"

def login(p, if_phone=False, first_name="John", last_name="Doe"):
    # step 1: Login
    permissions = ['clipboard-read']
    browser = p.chromium.launch(headless=False, slow_mo=1000, args=["--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"])

    if if_phone:
        phone = p.devices['iPhone 12 Pro']
        context = browser.new_context(**phone, permissions=permissions, reduced_motion='no-preference')
    else:
        context = browser.new_context()

    # Start tracing
    context.tracing.start(screenshots=True, snapshots=True, sources=True)

    page = context.new_page()
    page.goto('https://dev.new.expensify.com:8082/') 

    phone_or_email_input = page.locator('input[type="email"]')
    phone_or_email_input.fill(user_id)

    continue_button = page.locator('button[tabindex="0"]')
    continue_button.click()
    magic_code = "123456"

    validate_code_input = page.locator('input[name="validateCode"]')
    validate_code_input.fill(magic_code)

    return browser, page, context
    

def test_50961():
    with sync_playwright() as p:
        browser, page, context = login(p, False)
        try:
            chat_name = "John Doe (you)"
            page.get_by_label("Navigates to a chat").get_by_text(chat_name, exact=True).click()
            page.locator('button[aria-label="Create"]').click()
            page.locator('div[aria-label="Track expense"][role="menuitem"]').click()
            page.get_by_test_id("IOURequestStartPage").locator('button[aria-label="Distance"]').click()
            page.get_by_test_id("IOURequestStartPage").locator('button[aria-label="Back"]').click()
            page.locator('button[aria-label="Create"]').click()
            page.locator('div[aria-label="Track expense"][role="menuitem"]').click()
            page.get_by_test_id("IOURequestStartPage").locator('button[aria-label="Distance"]').click()
            page.get_by_test_id("IOURequestStartPage").get_by_text("Start").click()
            error_text = page.get_by_test_id("IOURequestStepWaypoint").locator('div[dir="auto"]', has_text="Oops, this page cannot be found")
            expect(error_text).not_to_be_visible()
            expected_locator = page.get_by_test_id("IOURequestStepWaypoint").locator('div[aria-label="Address"]')
            expect(expected_locator).to_be_visible()
        finally:
            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            context.tracing.stop(path=trace_path)
            trace_cleaner(trace_path)
            browser.close()
