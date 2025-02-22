from playwright.sync_api import sync_playwright, expect


def generate_random_email():
    email = f"newtestuser+{1739827257}@gmail.com"

    return email


def test_task():
    with sync_playwright() as p:
        email = generate_random_email()
        browser = p.chromium.launch(headless=False, slow_mo=1000, args=[
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
        ])
        page = browser.new_page()

        page.goto("https://dev.new.expensify.com:8082/")
        page.get_by_test_id("username").click()
        page.get_by_test_id("username").fill(email)
        page.get_by_test_id("username").press("Enter")
        page.get_by_role("button", name="Join").click()
        page.get_by_label("Get paid back by my employer").click()
        page.get_by_role("textbox", name="First name").fill("test")
        page.get_by_role("textbox", name="First name").press("Tab")
        page.get_by_role("textbox", name="Last name").fill("user")
        page.get_by_role("button", name="Continue").click()
        
        page.goto("https://dev.new.expensify.com:8082/settings/wallet")
        
        expect(page.get_by_text("Expensify Wallet")).to_be_visible()
        expect(page.get_by_text("Send and receive money with friends.")).to_be_visible()

        browser.close()