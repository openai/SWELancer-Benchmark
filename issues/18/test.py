import imaplib
import email
import re
from email.header import decode_header
from playwright.sync_api import sync_playwright, expect

GMAIL_NAME = "nomandevtur+54794.2"
GMAIL_APP_PASSWORD = "tpye xlsj axyq nltq"


def get_test_user_info(seed = None, first_name = None, last_name = None):
    if first_name is None:
        first_name = GMAIL_NAME

    if last_name is None:
        last_name = ""

    email = f"{GMAIL_NAME}+{seed}@gmail.com" if seed is not None else f"{GMAIL_NAME}@gmail.com"
    
    return {"email": email, "password": GMAIL_APP_PASSWORD, "first_name": first_name, "last_name": last_name}


def select_activity(page, first_name, last_name, activity_text):
    
    # Select activity in onboarding page and click Continue
    page.get_by_label(activity_text).click()

    # Enter first name, last name and click continue
    page.get_by_role("textbox", name="First name").fill(first_name)
    page.get_by_role("textbox", name="Last name").fill(last_name)
    page.get_by_role("button", name="Continue").last.click()


def login_user(page, user_info, activity_text="Track and budget expenses"):
    # Clear cookies, local storage, and session storage
    page.context.clear_cookies()

    page.goto('https://dev.new.expensify.com:8082/', timeout=60000)  # 60 seconds
    page.wait_for_load_state('load', timeout=60000)

    page.get_by_test_id("username").fill(user_info["email"])
    page.get_by_role("button", name="Continue").click()

    join_button = page.get_by_role("button", name="Join")
    validate_code_input = page.locator('input[data-testid="validateCode"]')

    page.wait_for_timeout(1000)
    magic_code = "123456"
    print(f"Magic code: {magic_code}")
    validate_code_input.fill(magic_code)

    page.wait_for_timeout(3000)

    select_activity_dialog = page.get_by_text("What do you want to do today?")
    if select_activity_dialog.count() > 0:
        select_activity(page, user_info["first_name"], user_info["last_name"], activity_text)


def launch_app(pw, headless=False, device=None, geolocation=None):
    browser = pw.chromium.launch(
        proxy = {"server": "http://localhost:8080"}, 
        headless = False, 
        args = ["--no-sandbox", "--disable-dev-shm-usage", "--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"], 
        slow_mo = 1500
    )

    context_args = {"viewport": {"width": 1324, "height": 740}}
    if device:
        context_args.update(pw.devices[device])
    if geolocation:
        context_args["geolocation"] = geolocation
        context_args["permissions"] = ["geolocation"]
    context = browser.new_context(**context_args)
    page = context.new_page()
    return browser, context, page

    
def test_54794():
    with sync_playwright() as p:
        
        user_info = get_test_user_info()

        browser, context, page = launch_app(p)
        login_user(page, user_info)

        page.wait_for_timeout(3000)

        # prerequisite - One workspace should already be created
        page.get_by_label("My settings").click()
        page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()
        page.get_by_label("row").click()
        page.get_by_label("Members").click()
        page.get_by_role("button", name="Invite member").click()
        page.get_by_test_id("selection-list-text-input").fill("a@a.com")
        page.wait_for_timeout(1000)
        page.locator("button[aria-label='a@a.com']").last.click()
        page.get_by_role("button", name="Next").click()

        role_element = page.get_by_test_id("WorkspaceInviteMessagePage").get_by_text("Role")
        assert role_element.is_visible(), "Test failed! 'Role' element is not visible."
        role_element.click()
        
        admin_button = page.locator("button[aria-label='Admin']")
        auditor_button = page.locator("button[aria-label='Auditor']")
        member_button = page.locator("button[aria-label='Member']")

        
        assert admin_button.count() > 0, "Test failed! 'Admin' button is missing."
        assert auditor_button.count() > 0, "Test failed! 'Auditor' button is missing."
        assert member_button.count() > 0, "Test failed! 'Member' button is missing."

        page.wait_for_timeout(3000)
        page.close()
        browser.close()
