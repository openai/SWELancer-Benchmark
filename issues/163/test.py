from playwright.sync_api import  expect, sync_playwright

NEWDOT_URL = "https://dev.new.expensify.com:8082/"

def test_onboarding_tasks_in_adminsroom():
    
    with sync_playwright() as p:
        browser =  p.chromium.launch(headless=False, slow_mo=1000, 
                                     args=['--disable-web-security',
                                           "--disable-features=IsolateOrigins,site-per-process",
                                           "--ignore-certificate-errors"],
                                            proxy={"server": "http://localhost:8080"})
        context = browser.new_context()
        page = context.new_page()
        #generate random email to logon
        email = 'fwzyhstrzc@whicg.com'

        # Go to ND and enter the random email
        page.goto(NEWDOT_URL)  
        page.locator('input[type="email"]').fill(email)
        page.keyboard.press('Enter')
        page.get_by_role("button", name="Join").click()

        #pick the desired options in Onboarding menu
        page.get_by_label("Manage my team's expenses").click()
        page.get_by_label("-10 employees").click()
        page.get_by_role("button", name="Continue").click()
        page.get_by_label("QuickBooks Online").click()
        page.get_by_test_id("BaseOnboardingAccounting").get_by_role("button", name="Continue").click()
        page.wait_for_timeout(1000)

        #navigate to admins chatroom and check for tasks 
        page.get_by_text('#admins').last.click()
        page.wait_for_timeout(1000)
        expect(page.get_by_text('Create a workspace')).to_be_in_viewport()

        browser.close()
        
        