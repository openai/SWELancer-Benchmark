import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
from playwright.sync_api import sync_playwright, expect
from playwright._impl._page import Page
from utils.trace_cleaner import trace_cleaner

# Expensify app URL
NEWDOT_URL = "https://127.0.0.1:8082/"
OLDDOT_URL = "http://localhost:9000/"
EMAIL = "t1533148@gmail.com"  # for example test+1234@gmail.com
PASSWORD = "logb hzkg pkfk kskg"  # it will be something like "sdib pxop ovyl uawy"

def verify_delete_confirmation_modal_back_out(page: Page):
    # Step 1: Track a distance expense
    page.get_by_label("Start chat (Floating action)").click()
    page.get_by_label("Track expense").click()
    try:
        # for the new user, the tutorial is shown, so close it
        page.get_by_label("Don't show me this again").click()
        page.get_by_role("button", name="Got it").click()
    except:
        pass
    page.get_by_label("Distance").click()
    page.wait_for_timeout(2000)
    page.get_by_test_id("IOURequestStartPage").get_by_role("button", name="Start").click()
    page.wait_for_timeout(2000)
    page.get_by_test_id("IOURequestStepWaypoint").get_by_role("textbox").fill("Golden Gate Bridge Vista Point")
    page.wait_for_timeout(2000)
    page.get_by_text("Golden Gate Bridge Vista Point", exact=True).first.click()
    page.wait_for_timeout(2000)
    page.get_by_role("button", name="Stop").click()
    page.wait_for_timeout(2000)
    page.get_by_test_id("IOURequestStepWaypoint").get_by_role("textbox").fill("Telegraph Hill")
    page.wait_for_timeout(2000)
    page.get_by_text("Telegraph Hill", exact=True).first.click()
    page.wait_for_timeout(2000)
    # Wait for Next button to be clickable
    page.locator('button[style="cursor: pointer;"]').wait_for()
    page.wait_for_timeout(2000)
    for _ in range(3):
        try:
            # sometimes the button is stil not clickable, so wait for it to be clickable
            page.get_by_role("button", name="Next").nth(1).click()
            page.wait_for_timeout(2000)
            page.get_by_role("button", name="Track expense").wait_for(timeout=1000)
            page.wait_for_timeout(2000)
            break
        except:
            pass
    page.get_by_role("button", name="Track expense").click()
    page.wait_for_timeout(2000)

    try:
        # Wait for the Receipt to be created, sometimes it takes more than 30 seconds
        page.get_by_label("Cash").locator("img").wait_for(timeout=120000)
    except:
        assert False, "Receipt was not able to load due to network issues"

    # Step 2: Open the receipt and click on triple dots
    page.get_by_label("Cash").locator("img").click()
    page.get_by_label("View attachment").click()
    page.get_by_label("More").click()

    # Step 3: Wait for the menu to open
    page.get_by_label("Download").wait_for()

    # Step 4: Click on Delete receipt if it is shown
    # This is to ensure that the test does not fail if the receipt is not editable
    if page.get_by_label("Delete receipt").is_visible():
        page.get_by_label("Delete receipt").click()
        # wait for the modal to open
        page.get_by_role("button", name="Delete").wait_for()
    
    # back out
    page.locator("body").press("Escape")
    
    # Step 5: Verify that the Receipt page is shown but the Delete confirmation modal is not shown
    expect(page.get_by_role("dialog").get_by_text("Receipt", exact=True)).to_have_count(1)
    expect(page.get_by_role("button", name="Delete")).to_have_count(0)


def test_delete_confirmation_modal_back_out_in_receipt_page():
    """
    Test to verify that the Delete confirmation modal in Receipt page backs out correctly
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel='chrome', headless=True, slow_mo=500,
            proxy={"server": "http://127.0.0.1:8080/"},
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
            page = context.new_page()
            page.wait_for_timeout(1000)

            page.goto('https://127.0.0.1:8082/')
            # Step 2: Enter email and click continue
            page.locator('input[type="email"]').fill(EMAIL)
            page.locator('button[tabindex="0"]').click()
            # Wait for OTP
            page.wait_for_timeout(5000)
            otp = '123456'
            page.get_by_test_id("validateCode").fill(otp)

            # Step 3: Verify that Delete confirmation modal in Receipt page backs out correctly
            verify_delete_confirmation_modal_back_out(page)

        except Exception as e:
            # Re-raise the exception after ensuring the trace is captured
            raise e
        finally:
            # Stop and export the trace
            context.tracing.stop()
            context.tracing.export(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")

            # Close browser
            context.close()
            browser.close()
