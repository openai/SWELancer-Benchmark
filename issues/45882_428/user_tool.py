import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
from playwright.sync_api import TimeoutError, expect, sync_playwright
from utils.trace_cleaner import trace_cleaner

EXPENSIFY_URL = "https://dev.new.expensify.com:8082/"
EMAIL = "t1533148@gmail.com"  # for example test+1234@gmail.com
PASSWORD = "logb hzkg pkfk kskg"  # it will be something like "sdib pxop ovyl uawy"


# Utility to generate a random email
def generate_random_email():
    timestamp = int(time.time())
    return "t1533148+173350934@gmail.com"


def login_user(page, email, first_name="John", last_name="Doe"):
    """
    Log into the Expensify app.
    """
    # Open the Expensify app
    page.goto(EXPENSIFY_URL)
    # Login user
    page.get_by_test_id("username").fill(email)
    page.get_by_role("button", name="Continue").click()
    # Check if OTP is required for the login
    try:
        expect(page.get_by_test_id("SignInPage").get_by_test_id("validateCode")).to_be_visible(timeout=5000)
    except AssertionError:
        # If not required, expect the join button to appear and click the button
        page.get_by_test_id("SignInPage").get_by_role("button", name="Join").click()
    else:
        # Get the OTP and complete verification
        otp_code = '123456'
        page.get_by_test_id("SignInPage").get_by_test_id("validateCode").fill(otp_code)
        page.get_by_test_id("SignInPage").get_by_role("button", name="Sign in").click()
    # Check if onboarding is required
    try:
        expect(page.get_by_text("What do you want to do today?")).to_be_visible(timeout=5000)
    except AssertionError:
        pass
    else:
        # Complete the onboarding
        page.get_by_label("Track and budget expenses").click()
        page.get_by_role("textbox", name="First name").fill(first_name)
        page.get_by_role("textbox", name="Last name").fill(last_name)
        page.get_by_role("button", name="Continue").click()
        # Exit the Concierge chat, if opened by default
        try:
            page.get_by_role("button", name="Back").first.click(timeout=3000)
        except (AssertionError, TimeoutError):
            pass
    # Dismiss the "Get started here!" tool tip, if shown
    try:
        page.get_by_role("button", name="Close").click(timeout=3000)
    except (AssertionError, TimeoutError):
        pass
    # Expect the main screen to appear
    page.wait_for_timeout(5000)


def test_user_current_location_is_not_shown_under_recent_destinations_for_distance_expense_request():
    """
    Verify that user's current location is not shown under recent destinations while creating a distance expense request.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, slow_mo=500,
            proxy={"server": "http://127.0.0.1:8080/"},
            args=[
                "--ignore-certificate-errors",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process"
            ]
        )
        geolocation = {"longitude": 41.890221, "latitude": 12.492348}
        context_args = {
            "geolocation": geolocation,
            "permissions": ["geolocation"],
            "ignore_https_errors": True
        }
        context = browser.new_context(**context_args)
        page = context.new_page()
        page.wait_for_timeout(1000)
        email = generate_random_email()
        first_name = "Fname"
        last_name = "Lname"

        # Start tracing
        context.tracing.start(title="test_trace", screenshots=True, snapshots=True)
        try:
            login_user(page, email, first_name=first_name, last_name=last_name)

            # Create a new workspace
            page.get_by_role("button", name="My settings").click()
            page.get_by_test_id("InitialSettingsPage").get_by_role("menuitem", name="Workspaces", exact=True).click()
            page.get_by_test_id("WorkspacesListPage").get_by_role("button", name="New workspace").first.click()

            # Read the workspace name
            texts = page.get_by_test_id("WorkspacePageWithSections").get_by_role("menuitem").all_inner_texts()
            workspace_name = texts[0].split("\n")[-1]

            # Go to the workspace chat
            page.get_by_test_id("WorkspaceInitialPage").get_by_role("button", name="Back").click()
            page.get_by_role("button", name="Inbox", exact=True).click()
            page.get_by_test_id("BaseSidebarScreen").get_by_text(workspace_name, exact=True).click()

            # Create a distance expense request
            page.get_by_test_id("report-actions-view-wrapper").get_by_role("button", name="Create", exact=True).click()
            page.get_by_role("menuitem", name="Submit expense", exact=True).click()
            page.get_by_test_id("IOURequestStartPage").get_by_role("button", name="Distance", exact=True).click()
            page.get_by_test_id("IOURequestStartPage").get_by_role("menuitem", name="Start", exact=True).click()
            page.wait_for_timeout(1000)
            page.get_by_test_id("IOURequestStepWaypoint").get_by_label("Use current location", exact=True).click()
            page.wait_for_timeout(10000)
            page.get_by_test_id("IOURequestStartPage").get_by_role("menuitem", name="Stop", exact=True).click()
            page.wait_for_timeout(1000)
            page.get_by_test_id("IOURequestStepWaypoint").get_by_role("textbox").fill("Germany")
            page.wait_for_timeout(1000)
            page.get_by_test_id("IOURequestStepWaypoint").get_by_text("Germany", exact=True).nth(1).click()
            page.wait_for_timeout(15000)
            page.get_by_test_id("IOURequestStartPage").get_by_role("button", name="Next", exact=True).last.click()
            page.get_by_test_id("IOURequestStepConfirmation").get_by_role("button", name="Submit", exact=False).click()

            # Reload the page
            # This is to ensure that the recent waypoints gets updated
            page.reload()
            page.wait_for_load_state("domcontentloaded")
            page.wait_for_timeout(3000)

            # Create another distance expense request
            page.get_by_test_id("report-actions-view-wrapper").get_by_role("button", name="Create", exact=True).click()
            page.get_by_role("menuitem", name="Submit expense", exact=True).click()
            page.get_by_test_id("IOURequestStartPage").get_by_role("button", name="Distance", exact=True).click()
            page.get_by_test_id("IOURequestStartPage").get_by_role("menuitem", name="Start", exact=True).click()

            # Wait for the recent destinations to appear
            expect(
                page.get_by_test_id("IOURequestStepWaypoint").get_by_text("Recent destinations", exact=True)
            ).to_be_visible(timeout=5000)

            # Add delay to make the recent destinations visible to the user running the test
            page.wait_for_timeout(3000)

            # Verify that the user current location is not shown under recent destinations
            current_location = f"Lat: {geolocation['latitude']} Lng: {geolocation['longitude']}"
            assert_message = "The user current location must not be shown under recent destinations"
            expect(
                page.get_by_test_id("IOURequestStepWaypoint").get_by_text(current_location, exact=True),
                assert_message,
            ).not_to_be_visible()

        finally:
            # Stop and export tracing, then clean the trace
            context.tracing.stop()
            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            context.tracing.export(trace_path)
            trace_cleaner(trace_path)
            context.close()
            browser.close()
