from playwright.sync_api import sync_playwright, expect


user_email = "totherandomuser+52599@gmail.com"


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
                "--disable-features=IsolateOrigins,site-per-process"],
                slow_mo=500)
        
        context = browser.new_context()
        page = login(p, context)

        page.get_by_label("Start chat (Floating action)").click()
        page.get_by_label("Start chat", exact=True).click()
        page.get_by_test_id("selection-list-text-input").click()
        page.get_by_test_id("selection-list-text-input").fill("totherandomuser")
        page.get_by_test_id("selection-list").get_by_label("totherandomuser+").click()
        page.wait_for_timeout(2000)
        page.get_by_test_id("report-screen-7998596991069043").get_by_label("Search").click()
        page.wait_for_timeout(2000)
        page.get_by_label("Search in totherandomuser+").click()
        page.wait_for_timeout(2000)

        locator = page.get_by_test_id("search-router-text-input")

        scroll_left = locator.evaluate("el => el.scrollLeft")
        
        assert scroll_left > 0, "The cursor should be at the end"