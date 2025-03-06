import imaplib
import email
import re
from email.header import decode_header
from playwright.sync_api import sync_playwright, expect

GMAIL_NAME = "nomandevtur+54741.2"
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

    
def test_54741():
    with sync_playwright() as p:
        
        user_info = get_test_user_info()

        browser, context, page = launch_app(p)
        login_user(page, user_info)

        page.wait_for_timeout(3000)

        page.get_by_label("My settings").click()
        page.get_by_label("Wallet").click()
        page.get_by_text("Add bank account").click()
        page.get_by_test_id("selection-list-text-input").fill("Iran")

        page.wait_for_timeout(1000)
        # Check For country
        btn_locator = page.locator("button[aria-label='Iran']")

        if btn_locator.count() > 0:
            assert False, "Test failed! Button with aria-label='Iran' is present."
        else:
            assert True

        page.wait_for_timeout(1000)

        # Check For Currency
        page.get_by_test_id("selection-list-text-input").fill("Norway")
        page.get_by_label("Norway").click()
        page.get_by_role("button", name="Next").click()
        page.get_by_text("Currency").click()
        page.get_by_test_id("selection-list-text-input").fill("Irr")

    
        btn_locator = page.locator("button[aria-label='IRR - ﷼']")

        if btn_locator.count() > 0:
            assert False, "Test failed! Button with aria-label='IRR - ﷼' is present."
        else:
            assert True

        
        page.wait_for_timeout(3000)
        page.close()
        browser.close()
