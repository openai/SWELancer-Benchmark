from playwright.sync_api import sync_playwright, expect
from playwright._impl._browser import Browser
from playwright._impl._page import Page
from playwright.sync_api._context_manager import PlaywrightContextManager

# Expensify app URL
NEWDOT_URL = "https://dev.new.expensify.com:8082"

def login_user(p: PlaywrightContextManager, first_name="Milan", last_name="T") -> tuple[Browser, Page, str]:
    email = "rgarciatammy4+17398301472330@gmail.com"
    # Launch chromiun and open new page
    browser = p.chromium.launch(headless=False, args=[
        "--ignore-certificate-errors",
        "--disable-web-security",
        "--disable-features=IsolateOrigins,site-per-process"
    ], slow_mo=1000, proxy = {"server": "http://127.0.0.1:8080/"})
    context = browser.new_context(viewport={"width": 360, "height": 680})
    page = context.new_page()

    # Step 1: Open expensify url
    page.goto('https://dev.new.expensify.com:8082/') 

    # Step 2: Enter email and click continue
    page.locator('input[type="email"]').fill(email)
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(1000)

    # Step 3: Click join button
    page.get_by_role("button", name="Join").click()

    if(page.locator("text='Track and budget expenses'").is_visible() == False):
        page.reload()
        page.wait_for_timeout(1000)
    # Step 4: Select 'Track and budget expenses' in onobarding page and click Continue
    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()
    page.wait_for_timeout(1000)

    # Step 5: Enter first name, last name and click continue
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()
    page.wait_for_timeout(1000)

    return browser, page, email

def test_header_height_issue():
    with sync_playwright() as pw:
        browser, page, email = login_user(pw, "A", "Local")
        if(page.get_by_text("Expensify").is_visible()):
            page.get_by_text("Concierge").last.click()
        element = page.locator("div[data-drag-area='true']")
        conceirge_header_height = element.last.bounding_box()['height']
        page.get_by_label("Back").click()
        page.get_by_text("A Local (you)").nth(0).click()
        chat_header_height = element.last.bounding_box()['height']
        assert conceirge_header_height == chat_header_height, f'Concerige header height: {conceirge_header_height} is not equal to chat header height: {chat_header_height}'

        # Close the browser
        browser.close()