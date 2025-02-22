from playwright.sync_api import sync_playwright, expect


def generate_random_email():
    email = f"newtestuser+{1740002436}@gmail.com"

    return email


def test_task():
    with sync_playwright() as p:
        email = generate_random_email()
        browser = p.chromium.launch(proxy = {"server": "http://localhost:8080"}, headless = False, args = ["--no-sandbox", "--disable-dev-shm-usage", "--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"], slow_mo = 1000, channel = "chromium")
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

        page.wait_for_timeout(3000)
        
        page.goto("https://dev.new.expensify.com:8082/")
        
        try:
            page.get_by_role('button', name="Task").filter(has_text="Take a 2-minute tour").click()
        except:
            page.get_by_role('button', name="Task").filter(has_text="Take a 2-minute tour").last.click()
        
        page.goto("https://dev.new.expensify.com:8082/concierge?navattic=completed")

        expect(page.get_by_role('button', name="Task").filter(has_text="Take a 2-minute tour").locator('div[aria-checked="true"]')).to_be_visible()

        browser.close()