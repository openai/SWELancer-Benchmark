import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from email.header import decode_header
from utils.trace_cleaner import trace_cleaner

expensify_email = "totherandomuser+50163@gmail.com"


def login(p, if_phone=False, first_name="John", last_name="Cena"):
    # step 1: Login
    permissions = ['clipboard-read', 'clipboard-write']
    browser = p.chromium.launch(headless=True, slow_mo=1000,
                                proxy={"server": "http://127.0.0.1:8080/"},
                                args=[
                                    "--ignore-certificate-errors",
                                    "--disable-web-security",
                                    "--disable-features=IsolateOrigins,site-per-process"
                                ])
    context_args = {}
    context_args["geolocation"] = {"latitude": 37.7749, "longitude": 122.4194}
    context_args["permissions"] = ["geolocation"]
    context_args["ignore_https_errors"] = True

    if if_phone:
        phone = p.devices['iPhone 12 Pro']
        context = browser.new_context(**phone, permissions=permissions, reduced_motion='no-preference')
    else:
        context = browser.new_context(**context_args)

    page = context.new_page()
    page.wait_for_timeout(5000)

    page.goto('https://127.0.0.1:8082/')

    # Step 1: Enter username and continue
    page.get_by_test_id("username").click()
    page.get_by_test_id("username").fill(expensify_email)
    page.get_by_role("button", name="Continue").click()
    magic_code = '123456'
    validate_code_input = page.locator('input[name="validateCode"]')
    validate_code_input.fill(magic_code)
    page.wait_for_timeout(1000)

    return browser, page, context


def test():
    with sync_playwright() as p:
        browser, page, context = login(p, False)

        # Start tracing
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        try:
            # Step 2: Go to Search Tab and click on rename.
            page.get_by_test_id("CustomBottomTabNavigator").get_by_label("Search").click()
            page.get_by_text("type:expense status:all").click()
            page.get_by_label("More").click()
            page.get_by_text("Rename").click()

            # Step 3: validate the close button
            page.wait_for_timeout(2000)
            is_clear_button_visible = False
            if page.get_by_label("Clear").is_visible():
                is_clear_button_visible = True

            assert is_clear_button_visible == True, "The clear button is not visible, it should be visible!!"
        except Exception as e:
            # Optionally log the error or re-raise
            raise e
        finally:
            # Stop tracing and save
            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")

            # Clean up
            context.close()
            browser.close()
