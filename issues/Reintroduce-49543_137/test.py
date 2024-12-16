import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright

NEWDOT_URL = "https://dev.new.expensify.com:8082/"
TEMP = 20034
EMAIL1 = f"dev091197+{TEMP}@gmail.com"


def new_dot_login(page, email):
  page.goto(NEWDOT_URL)
  page.locator('input[type="email"]').fill(email)
  page.get_by_role("button", name="Continue").nth(0).click()
  page.locator('input[data-testid="validateCode"]').fill("123456")


def test_expensify_0000():
   with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=[
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
        ])
    
    first_user_context = browser.new_context(
      ignore_https_errors=True
    )
    page = first_user_context.new_page()

    new_dot_login(page, EMAIL1)

    page.get_by_label("My settings").click()
    
    page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").get_by_text("Workspaces").click()
    page.locator("button").filter(has_text=f"{f"WS-{TEMP}"}.default-").click()
    
    page.locator('div[aria-label="Tags"]').click()

    page.locator('button[aria-label="State"]').click()

    page.locator('button[aria-label="CA"]').first.click()
    
    page.wait_for_timeout(1000)

    # Verify that the tag rules should not be available for multi-tags
    assert not page.locator("text=Tag rules").is_visible(), "Fail: 'Tag rules' text is present in Tag Settings."

    browser.close()