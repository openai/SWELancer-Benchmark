import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect

# Function to check focus and fetch border-color
def check_focus(page):
    page.get_by_test_id("username").fill("aquasaddam+28553@gmail.com") # we need to use an already present account
    page.get_by_role("button", name="Continue").click()
    
    page.get_by_test_id("validateCode").press("ArrowRight")
    page.get_by_test_id("validateCode").press("ArrowRight")
    page.get_by_test_id("validateCode").press("ArrowRight")
    
    page.wait_for_timeout(5000)  # wait for 30 seconds, "Didn't receive a magic code?" appears after 30 seconds
    
    page.get_by_label("Didn't receive a magic code?").click()

    page.wait_for_timeout(2000)
    
    # Use Playwright's `locator` to locate the element with the complex selector
    element = page.locator('#root > div > div > div > div > div:nth-child(1) > div > div.css-view-175oi2r.r-flex-13awgt0 > div > div > div.css-view-175oi2r.r-flex-13awgt0 > div > div.css-view-175oi2r.r-bottom-1p0dtai.r-left-1d2f490.r-position-u8s1d.r-right-zchlnj.r-top-ipm5af.r-pointerEvents-12vffkv > div.css-view-175oi2r.r-flex-13awgt0.r-pointerEvents-12vffkv > div > div > div > div.css-view-175oi2r.r-flex-13awgt0 > div > div > div > div > div > div:nth-child(2) > div > div:nth-child(1) > div > div > div > div:nth-child(2) > form > div:nth-child(4) > div:nth-child(1) > div:nth-child(1) > div:nth-child(2) > div')

    # Check that the element's border-color is the expected RGB value
    expect(element).to_have_css('border-color', 'rgb(3, 212, 124)')
    page.wait_for_timeout(1000)


# Test execution function for pytest
def test_run():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True, 
            proxy={
                    'server': 'http://127.0.0.1:8080',  
                    },
            args=[
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                ],
            )
        context = browser.new_context()
        page = context.new_page()

        # open expensify
        page.goto('https://dev.new.expensify.com:8082/')

        check_focus(page)

        # Close context and browser
        context.close()
        browser.close()