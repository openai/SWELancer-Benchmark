from playwright.sync_api import sync_playwright, expect
from playwright._impl._browser import Browser
from playwright._impl._page import Page
from playwright.sync_api._context_manager import PlaywrightContextManager
from utils.trace_cleaner import trace_cleaner

# Expensify app URL
NEWDOT_URL = "https://dev.new.expensify.com:8082"
OLDDOT_URL = "http://127.0.0.1:9000/"

def login_user(p: PlaywrightContextManager, first_name="Milan", last_name="T") -> tuple[Browser, Page, str]:
    email = "rgarciatammy4+17397256036989@gmail.com"
    # Launch chromium and open new page
    browser = p.chromium.launch(headless=False, args=[
        "--ignore-certificate-errors",
        "--disable-web-security",
        "--disable-features=IsolateOrigins,site-per-process"
    ], slow_mo=3000, proxy={"server": "http://127.0.0.1:8080/"})
    context = browser.new_context()
    page = context.new_page()

    # Step 1: Open expensify url
    page.goto('https://dev.new.expensify.com:8082/') 

    # Step 2: Enter email and click continue
    page.locator('input[type="email"]').fill(email)
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(3000)

    # Step 3: Click join button
    page.get_by_role("button", name="Join").click()

    if(page.locator("text='Track and budget expenses'").is_visible() == False):
        page.reload()
        page.wait_for_timeout(3000)
    # Step 4: Select 'Track and budget expenses' in onobarding page and click Continue
    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()
    page.wait_for_timeout(3000)

    # Step 5: Enter first name, last name and click continue
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()
    page.wait_for_timeout(3000)

    return browser, page, email


def test_duplicate_rate_issue():
    with sync_playwright() as pw:
        browser, page, email = login_user(pw, "A", "Local")
        # Capture the context from page to manage tracing
        context = page.context
        # Start tracing with screenshots, snapshots, and sources enabled
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        trace_path = "/app/expensify/user_tool/output_browser1.zip"
        try:
            page.wait_for_timeout(3000)
            page.get_by_label("My settings").click()
            page.wait_for_timeout(3000)
            page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()
            page.wait_for_timeout(4000)
            page.get_by_label("New workspace").click()
            page.wait_for_timeout(3000)
            page.get_by_label("More features").click()
            page.wait_for_timeout(3000)
            page.get_by_label("Add, update, and enforce").click()
            page.wait_for_timeout(3000)
            page.get_by_label("Distance rates").click()
            page.wait_for_timeout(3000)
            page.get_by_role("button", name="Add rate").click()
            page.wait_for_timeout(3000)
            page.get_by_placeholder("0").fill("0.2")
            page.get_by_role("button", name="Save").click()
            page.wait_for_timeout(3000)
            page.get_by_role("button", name="Add rate").click()
            page.get_by_placeholder("0").fill("0.2")
            page.get_by_role("button", name="Save").click()
            page.wait_for_timeout(3000)

            # Check if the URL is still the same after clicking on Save button
            assert page.url[len(page.url)-3: len(page.url)] == "new", "Able to save duplicate rate"

            # Check if the error message indicator is displayed as error message is not stated in the issue and it can be different message when client update the code.
            # So only checking for the indicator since, we need to see the error message to validate the issue.
            expect(page.get_by_test_id("CreateDistanceRatePage").locator("circle")).to_be_visible()

        finally:
            # Stop tracing and export the trace file
            context.tracing.stop(path=trace_path)
            trace_cleaner(trace_path)
            browser.close()


if __name__ == "__main__":
    test_duplicate_rate_issue()
