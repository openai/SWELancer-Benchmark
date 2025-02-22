from playwright.sync_api import sync_playwright

user_email = "testuserexpensify1@gmail.com"
password = "aedyeaocujbrrcal"
user_id = "testuserexpensify1+155@gmail.com"

def login(p, if_phone=False, first_name="John", last_name="Doe"):
    
    # step 1: Login
    permissions = ['clipboard-read']
    browser = p.chromium.launch(headless=False, slow_mo=1000, args=["--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"])

    if if_phone:
        phone = p.devices['iPhone 12 Pro']
        context = browser.new_context(**phone, permissions=permissions, reduced_motion='no-preference')
    else:
        context = browser.new_context()

    page = context.new_page()

    page.goto('https://dev.new.expensify.com:8082/') 

    phone_or_email_input = page.locator('input[type="email"]')
    phone_or_email_input.fill(user_id)

    continue_button = page.locator('button[tabindex="0"]')
    continue_button.click()
    magic_code = "123456"

    validate_code_input = page.locator('input[name="validateCode"]')
    validate_code_input.fill(magic_code)

    return browser, page
    
def test_53992():
    with sync_playwright() as p:
        browser, page = login(p, False)
        chat_name = "John Doe (you)"
        amount = "12345678"
        page.locator('button[aria-label="Start chat (Floating action)"]').click()
        page.locator('div[aria-label="Create expense"][role="menuitem"]').first.click()
        page.get_by_test_id("IOURequestStartPage").locator('button[aria-label="Manual"]').click()
        page.locator('input[role="presentation"]').fill(amount)
        page.get_by_test_id("IOURequestStartPage").locator('button[aria-label="Select a currency"]').click()
        page.get_by_test_id("selection-list").locator('button[aria-label="ALL - ALL"]').click()
        
        # Define locators
        locator1 = page.get_by_test_id("IOURequestStartPage")
        locator2 = locator1.locator('#amountView')
        locator3 = locator1.locator('#numPadContainerView')

        # Get bounding boxes for alignment verification
        box1 = locator1.bounding_box()
        box2 = locator2.bounding_box()
        box3 = locator3.bounding_box()

        assert box1 is not None and box2 is not None and box3 is not None, "One or more elements could not be found."
        
        # Verify alignment (checking X positions are aligned)
        print(f"box1['x']: {box1['x']}, box2['x']: {box2['x']}, box3['x']: {box3['x']}")
        assert box1["x"] == box2["x"] == box3["x"], "Elements are not aligned properly on the X-axis."

        browser.close()