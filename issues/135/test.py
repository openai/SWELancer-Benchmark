import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect

NEWDOT_URL = "https://dev.new.expensify.com:8082/"
OLDDOT_URL = "http://localhost:9000/" 
EMAIL = "randomturing@gmail.com"
PASSWORD = "ryfo zezf tmlq xybs"

static_email = "randomturing+40121571@gmail.com"

def new_dot_login_join(page, email, first_name, last_name):
    page.goto(NEWDOT_URL)
    page.locator('input[type="email"]').fill(email)
    page.get_by_role("button", name="Continue").click()
    page.get_by_role("button", name="Join").click()

    page.locator("text='Track and budget expenses'").wait_for()
    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()

    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("form").get_by_role("button", name="Continue").click()


def test_expensify():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, slow_mo=1000, args=["--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"])

        first_user_context = browser.new_context(ignore_https_errors=True)
        page = first_user_context.new_page()
        first_user_email = static_email
        new_dot_login_join(page, first_user_email, first_name="Tester", last_name="U")

        page.get_by_label("Start chat (Floating action)").click()


        track_expense_icon = page.locator("svg path[d='M19 3.5c0 1.105-2.239 2-5 2s-5-.895-5-2 2.239-2 5-2 5 .895 5 2ZM14 7.5c1.57 0 3.084-.25 4.278-.729A6.64 6.64 0 0 0 19 6.433V7.5c0 1.105-2.239 2-5 2-.352 0-.696-.015-1.028-.042l-.003-1.383c0-.232-.036-.437-.096-.619.37.03.747.044 1.127.044ZM12.98 11.464l.008 1.995c.327.027.665.04 1.012.04 2.761 0 5-.895 5-2v-1.066a6.63 6.63 0 0 1-.722.338c-1.194.478-2.708.729-4.278.729-.344 0-.685-.012-1.02-.036ZM11 8.5c0 1.105-2.239 2-5 2s-5-.895-5-2 2.239-2 5-2 5 .895 5 2ZM6 12.5c1.57 0 3.083-.25 4.278-.729a6.63 6.63 0 0 0 .722-.338V12.5c0 1.104-2.239 2-5 2s-5-.896-5-2v-1.067c.238.13.482.242.722.338C2.916 12.25 4.43 12.5 6 12.5ZM6 16.5c1.57 0 3.083-.25 4.278-.729a6.63 6.63 0 0 0 .722-.338V16.5c0 1.105-2.239 2-5 2s-5-.895-5-2v-1.067c.238.13.482.242.722.338C2.916 16.25 4.43 16.5 6 16.5Z']")
        expect(track_expense_icon).to_be_visible()


        request_money_icon = page.locator("svg path[d='M3 1.1V19c0 .4.5.5.7.3l.7-.9c.2-.2.4-.2.6 0l1.1 1.3c.2.2.4.2.6 0l1.1-1.3c.2-.2.4-.2.6 0l1.1 1.3c.2.2.4.2.6 0l1.1-1.3c.2-.2.4-.2.6 0l1.1 1.3c.2.2.4.2.6 0l1.1-1.3c.2-.2.4-.2.6 0l.7.9c.2.3.7.1.7-.3V1.1c0-.4-.5-.5-.7-.3l-.7.9c-.2.2-.4.2-.6 0L13.5.4c-.2-.2-.4-.2-.6 0L12 1.7c-.2.2-.4.2-.6 0L10.3.4c-.2-.2-.4-.2-.6 0L8.5 1.7c-.2.2-.4.2-.6 0L6.8.3c-.2-.2-.4-.2-.6 0L5 1.7c-.2.2-.4.2-.6 0L3.7.8C3.5.5 3 .7 3 1.1zM7 5c-.6 0-1 .4-1 1s.4 1 1 1h6c.6 0 1-.4 1-1s-.4-1-1-1H7zm0 4c-.6 0-1 .4-1 1s.4 1 1 1h4c.6 0 1-.4 1-1s-.4-1-1-1H7zm-1 5c0-.6.4-1 1-1h6c.6 0 1 .4 1 1s-.4 1-1 1H7c-.6 0-1-.4-1-1z']")
        expect(request_money_icon).to_be_visible()


        new_workspace_button = page.locator('div[aria-label="New workspace"]')
        new_workspace_button.click()


        back_arrow_button = page.locator('button[aria-label="Back"]')
        back_arrow_button.click()

        inbox_menu = page.locator('button[aria-label="Inbox"]')
        inbox_menu.click()

        page.get_by_label("Last chat message preview").last.click()
        page.get_by_label("Create").last.click()



        track_expense_icon = page.locator("svg path[d='M19 3.5c0 1.105-2.239 2-5 2s-5-.895-5-2 2.239-2 5-2 5 .895 5 2ZM14 7.5c1.57 0 3.084-.25 4.278-.729A6.64 6.64 0 0 0 19 6.433V7.5c0 1.105-2.239 2-5 2-.352 0-.696-.015-1.028-.042l-.003-1.383c0-.232-.036-.437-.096-.619.37.03.747.044 1.127.044ZM12.98 11.464l.008 1.995c.327.027.665.04 1.012.04 2.761 0 5-.895 5-2v-1.066a6.63 6.63 0 0 1-.722.338c-1.194.478-2.708.729-4.278.729-.344 0-.685-.012-1.02-.036ZM11 8.5c0 1.105-2.239 2-5 2s-5-.895-5-2 2.239-2 5-2 5 .895 5 2ZM6 12.5c1.57 0 3.083-.25 4.278-.729a6.63 6.63 0 0 0 .722-.338V12.5c0 1.104-2.239 2-5 2s-5-.896-5-2v-1.067c.238.13.482.242.722.338C2.916 12.25 4.43 12.5 6 12.5ZM6 16.5c1.57 0 3.083-.25 4.278-.729a6.63 6.63 0 0 0 .722-.338V16.5c0 1.105-2.239 2-5 2s-5-.895-5-2v-1.067c.238.13.482.242.722.338C2.916 16.25 4.43 16.5 6 16.5Z']")
        expect(track_expense_icon).to_be_visible()


        request_money_icon = page.locator("svg path[d='M3 1.1V19c0 .4.5.5.7.3l.7-.9c.2-.2.4-.2.6 0l1.1 1.3c.2.2.4.2.6 0l1.1-1.3c.2-.2.4-.2.6 0l1.1 1.3c.2.2.4.2.6 0l1.1-1.3c.2-.2.4-.2.6 0l1.1 1.3c.2.2.4.2.6 0l1.1-1.3c.2-.2.4-.2.6 0l.7.9c.2.3.7.1.7-.3V1.1c0-.4-.5-.5-.7-.3l-.7.9c-.2.2-.4.2-.6 0L13.5.4c-.2-.2-.4-.2-.6 0L12 1.7c-.2.2-.4.2-.6 0L10.3.4c-.2-.2-.4-.2-.6 0L8.5 1.7c-.2.2-.4.2-.6 0L6.8.3c-.2-.2-.4-.2-.6 0L5 1.7c-.2.2-.4.2-.6 0L3.7.8C3.5.5 3 .7 3 1.1zM7 5c-.6 0-1 .4-1 1s.4 1 1 1h6c.6 0 1-.4 1-1s-.4-1-1-1H7zm0 4c-.6 0-1 .4-1 1s.4 1 1 1h4c.6 0 1-.4 1-1s-.4-1-1-1H7zm-1 5c0-.6.4-1 1-1h6c.6 0 1 .4 1 1s-.4 1-1 1H7c-.6 0-1-.4-1-1z']")
        expect(request_money_icon).to_be_visible()


        page.get_by_text("Submit expense", exact=True).click()


        scan_icon = page.locator("svg path[d='M3 1.364V7h14V1.364a.4.4 0 0 0-.701-.265l-.748.861a.397.397 0 0 1-.602 0L13.801.638a.397.397 0 0 0-.602 0L12.051 1.96a.397.397 0 0 1-.602 0L10.301.638a.397.397 0 0 0-.602 0L8.551 1.959a.397.397 0 0 1-.602 0L6.801.638a.397.397 0 0 0-.602 0L5.051 1.959a.397.397 0 0 1-.602 0l-.748-.861A.4.4 0 0 0 3 1.364zM3 18.636V13h14v5.636a.4.4 0 0 1-.701.265l-.748-.861a.397.397 0 0 0-.602 0l-1.148 1.322a.397.397 0 0 1-.602 0l-1.148-1.322a.397.397 0 0 0-.602 0l-1.148 1.322a.397.397 0 0 1-.602 0L8.551 18.04a.397.397 0 0 0-.602 0l-1.148 1.322a.397.397 0 0 1-.602 0L5.051 18.04a.397.397 0 0 0-.602 0l-.748.861A.4.4 0 0 1 3 18.636zM2 9a1 1 0 0 0 0 2h16a1 1 0 0 0 0-2H2z']").first
        expect(scan_icon).to_be_visible()


        page.get_by_label("Manual").click()
        page.get_by_placeholder("0").fill("1000")
        page.locator("#numPadContainerView").get_by_role("button", name="Next").click()
        page.get_by_text("Merchant").click()
        page.get_by_role("textbox", name="Merchant").fill("merchant")
        page.get_by_role("button", name="Save").click()
        page.locator('button', has_text="Submit ").last.click()


        page.get_by_label("Start chat (Floating action)").click()
        submit_expense_icon = page.locator("svg path[d='M3 1.1V19c0 .4.5.5.7.3l.7-.9c.2-.2.4-.2.6 0l1.1 1.3c.2.2.4.2.6 0l1.1-1.3c.2-.2.4-.2.6 0l1.1 1.3c.2.2.4.2.6 0l1.1-1.3c.2-.2.4-.2.6 0l1.1 1.3c.2.2.4.2.6 0l1.1-1.3c.2-.2.4-.2.6 0l.7.9c.2.3.7.1.7-.3V1.1c0-.4-.5-.5-.7-.3l-.7.9c-.2.2-.4.2-.6 0L13.5.4c-.2-.2-.4-.2-.6 0L12 1.7c-.2.2-.4.2-.6 0L10.3.4c-.2-.2-.4-.2-.6 0L8.5 1.7c-.2.2-.4.2-.6 0L6.8.3c-.2-.2-.4-.2-.6 0L5 1.7c-.2.2-.4.2-.6 0L3.7.8C3.5.5 3 .7 3 1.1zM7 5c-.6 0-1 .4-1 1s.4 1 1 1h6c.6 0 1-.4 1-1s-.4-1-1-1H7zm0 4c-.6 0-1 .4-1 1s.4 1 1 1h4c.6 0 1-.4 1-1s-.4-1-1-1H7zm-1 5c0-.6.4-1 1-1h6c.6 0 1 .4 1 1s-.4 1-1 1H7c-.6 0-1-.4-1-1z']").last
        expect(submit_expense_icon).to_be_visible()   


        page.get_by_text("Track expense").click()
        page.get_by_role("button", name="Got it").click()
        page.get_by_placeholder("0").fill("100")
        page.locator("#numPadContainerView").get_by_role("button", name="Next").click()
        page.get_by_role("button", name="Track expense").click()


        page.get_by_label("Start chat (Floating action)").click()
        track_expense_icon = page.locator("svg path[d='M19 3.5c0 1.105-2.239 2-5 2s-5-.895-5-2 2.239-2 5-2 5 .895 5 2ZM14 7.5c1.57 0 3.084-.25 4.278-.729A6.64 6.64 0 0 0 19 6.433V7.5c0 1.105-2.239 2-5 2-.352 0-.696-.015-1.028-.042l-.003-1.383c0-.232-.036-.437-.096-.619.37.03.747.044 1.127.044ZM12.98 11.464l.008 1.995c.327.027.665.04 1.012.04 2.761 0 5-.895 5-2v-1.066a6.63 6.63 0 0 1-.722.338c-1.194.478-2.708.729-4.278.729-.344 0-.685-.012-1.02-.036ZM11 8.5c0 1.105-2.239 2-5 2s-5-.895-5-2 2.239-2 5-2 5 .895 5 2ZM6 12.5c1.57 0 3.083-.25 4.278-.729a6.63 6.63 0 0 0 .722-.338V12.5c0 1.104-2.239 2-5 2s-5-.896-5-2v-1.067c.238.13.482.242.722.338C2.916 12.25 4.43 12.5 6 12.5ZM6 16.5c1.57 0 3.083-.25 4.278-.729a6.63 6.63 0 0 0 .722-.338V16.5c0 1.105-2.239 2-5 2s-5-.895-5-2v-1.067c.238.13.482.242.722.338C2.916 16.25 4.43 16.5 6 16.5Z']").last
        expect(track_expense_icon).to_be_visible()  


        first_user_context.close() 