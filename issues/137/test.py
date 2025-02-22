from playwright.sync_api import  expect, sync_playwright

NEWDOT_URL = "https://dev.new.expensify.com:8082/"

def new_dot_login(page, email):
    page.goto(NEWDOT_URL)  
    
    page.locator('input[type="email"]').fill(email)
    page.keyboard.press('Enter')

    # Magic code entry
    page.wait_for_timeout(3000)
    my_otp_code = "123456"

    page.keyboard.type(my_otp_code)
    try:
        page.get_by_role("button", name="Sign in").click()
    except Exception:
        pass



def test_view_subscription_page():
    
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=False, 
        proxy = {"server": "http://127.0.0.1:8080/"},args=[
                            "--disable-web-security",
                             "--disable-features=IsolateOrigins,site-per-process"
        ])
        context = browser.new_context(**p.devices['Galaxy S5'])
        page = context.new_page()

        email = 't2815719+2891@gmail.com'
         # login user
        new_dot_login(page, email)

        #create new workspace and enable the feature
        page.get_by_label("My settings").click()
        page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()
        page.get_by_label("New workspace").click()
        page.get_by_label("More features").click()
        page.get_by_label("Set Per diem rates to control").click()
        page.get_by_role("button", name="Upgrade").click()
        page.get_by_role("link", name="View your subscription").click()
        page.wait_for_timeout(3000)
        
        
        #Check if view your subscription page is visible
        expect(page.get_by_test_id("SubscriptionSettingsPage").get_by_text("Subscription", exact=True)).to_be_in_viewport()
        

        
        browser.close()