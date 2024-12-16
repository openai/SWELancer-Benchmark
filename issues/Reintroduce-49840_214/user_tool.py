import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from utils.trace_cleaner import trace_cleaner

expensify_email = "nomandevtur+49840@gmail.com"
user_email = "nomandevtur@gmail.com"
password = "tpye xlsj axyq nltq"


def login(p, context):
    page = context.new_page()
    page.goto('https://dev.new.expensify.com:8082')

    # Step 1: Enter username and continue
    page.get_by_test_id("username").click()
    page.get_by_test_id("username").fill(expensify_email)
    page.get_by_role("button", name="Continue").click()

    # Step 2: Mark Inbox read and then get magic code from email
    magic_code = "123456"

    # Step 3: Fill in the magic code
    validate_code_input = page.locator('input[name="validateCode"]')
    expect(validate_code_input).to_be_visible()
    validate_code_input.fill(magic_code)
    page.wait_for_timeout(1000)

    return page


def test():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            proxy = {"server": "http://127.0.0.1:8080/"},
            slow_mo = 500,
            args=[
                "--ignore-certificate-errors",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process"
            ]
        )

        context_args = {}
        context_args["geolocation"] = {"latitude": 37.7749, "longitude": 122.4194}
        context_args["permissions"] = ["geolocation"]
        context_args["ignore_https_errors"] = True
        context = browser.new_context(**context_args)

        # Start recording the trace
        context.tracing.start(screenshots=True, snapshots=True, sources=True)

        try:
            page = login(p, context)

            # Step 2: Go to workspace and create an expense.
            page.get_by_test_id("630559259035264").click()
            page.get_by_label("Create").last.click()
            page.get_by_text("Submit expense", exact=True).click()
            page.get_by_label("Manual").click()
            page.get_by_placeholder("0").fill("500")
            page.locator("#numPadContainerView").get_by_role("button", name="Next").click()
            page.get_by_role("menuitem", name="Merchant Required").click()
            page.get_by_role("textbox", name="Merchant").click()
            page.get_by_role("textbox", name="Merchant").fill("task1")
            page.get_by_role("button", name="Save").click()
            page.get_by_role("button", name="Submit ").click()

            # Step 3: Change the language to Spanish.
            page.get_by_label("My settings").click()
            page.get_by_text("Preferences").click()
            page.get_by_label("English").click()
            page.get_by_label("Spanish").click()

            # Step 4: click on payelse where.
            page.get_by_label("Recibidos").click()
            page.get_by_test_id("630559259035264").click()
            page.locator("button div", has_text="de otra forma").last.click()

            payment_text_detected = False
            for _ in range(50):
                page_content = page.content()
                if "Payment complete" in page_content:
                    print("Detected 'Payment complete' text in page content!")
                    payment_text_detected = True
                    break
                page.wait_for_timeout(10)

            if not payment_text_detected:
                print("Payment complete text was not detected after retries.")

            assert payment_text_detected == False, "Detected 'Payment complete' text in page content!"

        except Exception as e:
            raise e
        finally:
            # Stop tracing and save to file
            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            browser.close()
