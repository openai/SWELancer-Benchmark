from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager

APP_URL = 'https://dev.new.expensify.com:8082/'
USER_EMAIL = 'testuserexpensify+1982318@gmail.com'


def login_user(p: PlaywrightContextManager, email_address):
    browser = p.chromium.launch(
        proxy = {"server": "http://localhost:8080"}, headless = False, args = ["--no-sandbox", "--disable-dev-shm-usage", "--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"], slow_mo = 1000, channel = "chromium")
    context = browser.new_context()
    page = context.new_page()
    page.goto(APP_URL)
    page.locator('input[type="email"]').fill(email_address)
    page.locator('button[tabindex="0"]').click()
    page.get_by_test_id("validateCode").fill("123456")
    return browser, context, page


def test():
    with sync_playwright() as p:
        browser, _, page = login_user(p, USER_EMAIL)
        page.wait_for_timeout(2000)
        page.evaluate('Onyx.merge("betas", ["newDotPerDiem"])')
        page.wait_for_timeout(2000)
        page.locator('button[aria-label="Start chat (Floating action)"]').click()
        page.get_by_role('menuitem', name='Create expense').click()
        page.locator('button[aria-label="Per diem"]').click()
        page.get_by_test_id('selection-list').locator('button[aria-label="Albanien (2020)"]').click()
        page.get_by_test_id('IOURequestStepTime').get_by_label('10', exact=True).first.click()
        page.get_by_test_id('IOURequestStepTime').get_by_label('11', exact=True).last.click()
        save_btn = page.get_by_role('button', name='Save')
        save_btn.click()
        page.get_by_role('menuitem', name='Subrate').click()
        page.get_by_role('button', name='Dinner').click()
        input = page.get_by_role("form").get_by_role("textbox")
        input.fill('1')
        save_btn.click()
        page.get_by_role('menuitem', name='Dinner, Qty: 1').click()
        input.fill('888')
        save_btn.click()
        page.get_by_test_id("IOURequestStepConfirmation").get_by_label("Back").click()
        expect(input).to_have_value(value='888', timeout=1000)
        browser.close()
