import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
import re
import random
from utils.email_handler import EmailHandler
from utils.trace_cleaner import trace_cleaner  # <--- Added import

# Expensify app URL
NEWDOT_URL = "https://dev.new.expensify.com:8082/"
OLDDOT_URL = "http://localhost:9000/"

EMAIL = "testingq186@gmail.com"
PASSWORD = "kkfr hqiv yuxq rbso"
EMAIL_ADMIN = "testingq186+121224_admin@gmail.com"
EMAIL_SUBMITTER = "testingq186+121224_submitter@gmail.com"
EMAIL_APPROVER1 = "testingq186+121224_approver1@gmail.com"
EMAIL_APPROVER2 = "testingq186+121224_approver2@gmail.com"

# True when testing the flow file
# False while recording 
TESTING_FLOW = True

def new_dot_login(page, email, password):
    page.goto(NEWDOT_URL)

    with EmailHandler(email, password) as email_handler:
        if not TESTING_FLOW:
            email_handler.clean_inbox()  # Clean inbox

        page.locator('input[type="email"]').fill(email)
        page.get_by_role("button", name="Continue").click()
        # Wait for OTP
        otp = email_handler.read_otp_code() if not TESTING_FLOW else "123456"
        page.get_by_test_id("validateCode").fill(otp)
    page.get_by_text("Concierge").last.wait_for()

def _test_part_admin(context, email_address, password):
    page = context.new_page()
    new_dot_login(page, email_address, password)
    page.get_by_label("My settings").click()
    page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").get_by_text("Workspaces").click()
    page.get_by_role("button", name="row").first.click()
    page.get_by_text("Members").click()
    page.get_by_text("Workflows").click()
    page.get_by_text("More features").click()
    # Run Test
    # Removed context.close() so we can manage it externally

def _test_part_submitter(context, email_address, password):
    page = context.new_page()
    new_dot_login(page, email_address, password)
    try:
        page.get_by_label("Close").click()
    except:
        pass
    rand_num = random.randint(10,999)
    page.get_by_text("AAA Workspace").nth(0).click()
    page.get_by_label("Create").last.click()
    page.get_by_text("Submit expense", exact=True).click()
    page.get_by_label("Manual").click()
    page.get_by_placeholder("0").click()
    page.get_by_placeholder("0").fill(f"{rand_num}")
    page.locator("#numPadContainerView").get_by_role("button", name="Next").click()
    page.get_by_text("Merchant").click()
    page.get_by_role("textbox", name="Merchant").fill(f"M{rand_num}")
    page.get_by_role("button", name="Save").click()
    page.get_by_role("button", name="Submit").last.click()
    # Removed context.close() so we can manage it externally

def _test_part_approver2(context, email_address, password):
    page = context.new_page()
    new_dot_login(page, email_address, password)
    try:
        page.get_by_label("Close").click()
    except:
        pass
    page.get_by_text(EMAIL_SUBMITTER).first.click()

    expect(page.get_by_label("View details").get_by_role("button", name="Submit", exact=True)).not_to_be_visible()

    # Removed context.close() so we can manage it externally

def test_expensify_48778():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="chrome",
            headless=True,
            args=["--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process" ],
            proxy={"server": "http://localhost:8080"},
            slow_mo=500
        )

        context_args = {}
        context_args["geolocation"] = {"latitude": 37.7749, "longitude": 122.4194}
        context_args["permissions"] = ["geolocation"]
        context_args["ignore_https_errors"] = True

        # If needed, you could uncomment and do admin test:
        # admin_context = browser.new_context(**context_args)
        # admin_context.tracing.start(screenshots=True, snapshots=True)
        # try:
        #     _test_part_admin(admin_context, EMAIL_ADMIN, PASSWORD)
        # except Exception as e:
        #     print(f"Error in _test_part_admin: {e}")
        # finally:
        #     admin_context.tracing.stop(path="/app/expensify/user_tool/output_browser3.zip")
        #     trace_cleaner("/app/expensify/user_tool/output_browser3.zip")
        #     admin_context.close()

        # Submitter
        submitter_context = browser.new_context()
        submitter_context.tracing.start(screenshots=True, snapshots=True)
        try:
            _test_part_submitter(submitter_context, EMAIL_SUBMITTER, PASSWORD)
        except Exception as e:
            print(f"Error in _test_part_submitter: {e}")
        finally:
            submitter_context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            submitter_context.close()

        # Approver2
        approver2_context = browser.new_context()
        approver2_context.tracing.start(screenshots=True, snapshots=True)
        try:
            _test_part_approver2(approver2_context, EMAIL_APPROVER2, PASSWORD)
        except Exception as e:
            print(f"Error in _test_part_approver2: {e}")
        finally:
            approver2_context.tracing.stop(path="/app/expensify/user_tool/output_browser2.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser2.zip")
            approver2_context.close()

        browser.close()
