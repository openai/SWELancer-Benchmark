from playwright.sync_api import sync_playwright, expect

user_email = "totherandomuser+53880@gmail.com"


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
                        slow_mo=1000)
        
        context = browser.new_context()
        page = login(p, context)
      
        page.get_by_label("Reports").click()

        try:
            # If a saved filter is already there delete it.
            page.get_by_label("More").click()
            page.get_by_test_id("PopoverMenuItem-Delete").click()
            page.get_by_label("Delete").click()
        except:
            pass

        # save a currency filter.
        page.get_by_role("button", name="Filters").click()
        page.get_by_role("menuitem", name="Currency").click()
        page.get_by_test_id("base-list-item-AED - Dhs").get_by_label("AED - Dhs").click()
        page.get_by_role("button", name="Save").click()
        page.get_by_role("button", name="Save search").click()
        page.wait_for_timeout(2000)


        # reset the filter.
        page.get_by_role("button", name="Filters").click()
        page.get_by_role("link", name="Reset filters").click()
        page.get_by_role("button", name="View results").click()
        page.wait_for_timeout(2000)

        # again select a filter and save
        page.get_by_role("button", name="Filters").click()
        page.get_by_test_id("SearchAdvancedFiltersPage").get_by_role("menuitem", name="Currency").click()
        page.get_by_test_id("base-list-item-AED - Dhs").get_by_label("AED - Dhs").click()
        page.get_by_role("button", name="Save").click()
        page.get_by_role("button", name="Save search").click()
        page.wait_for_timeout(2000)

        # make sure that the Nothing to show button is there.
        expect(page.get_by_text("Nothing to show").nth(1)).to_be_visible()
