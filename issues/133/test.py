
from playwright.sync_api import  sync_playwright

NEWDOT_URL = "https://dev.new.expensify.com:8082/"


def new_dot_login(page, email):
    page.goto(NEWDOT_URL)  
    
    page.locator('input[type="email"]').fill(email)
    page.keyboard.press('Enter')

    # Magic code entry
    page.wait_for_timeout(3000)
    my_otp_code = '123456'

    page.keyboard.type(my_otp_code)
    try:
        page.get_by_role("button", name="Sign in").click()
    except Exception:
        pass



def test_same_tab():
    
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=False, 
         proxy = {"server": "http://127.0.0.1:8080/"},args=[
                            "--disable-web-security",
                             "--disable-features=IsolateOrigins,site-per-process"
        ])
        context = browser.new_context()
        page = context.new_page()

        email = 't2815719+2893@gmail.com'
         # login user
        new_dot_login(page, email)

        new_pages = []
        context.on("page", lambda new_page: new_pages.append(new_page))
        
        #navigate to settings
        page.get_by_label("My settings").click()
        page.get_by_label("Switch to Expensify Classic").click()

        #fillout neccessary info to continue with operation
        page.get_by_label("I don't understand how to use").click()
        page.get_by_role("button", name="Next").click()
        page.get_by_role("textbox", name="Your response").fill("test")
        page.get_by_role("button", name="Next").click()
        page.get_by_role("button", name="Switch to Expensify Classic").click()
        page.wait_for_timeout(50000) #waiting for page to load and fail
       

        #test title of page is loading
        assert  len(new_pages) == 0 ,'Switch to classic should open in same tab'
        
        browser.close()