from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page
from utils.trace_cleaner import trace_cleaner


# Utility to generate an email
def generate_email():
    timestamp = '639000'
    return f"freelanceapptest+{timestamp}@gmail.com"


# Function to log in the user and complete onboarding steps
def login_user(p: PlaywrightContextManager, first_name="Milan", last_name="T") -> tuple[Browser, Page, str]:
    # Launch Chromium and open a new page
    browser = p.chromium.launch(
        proxy={"server": "http://localhost:8080"}, headless=False, args=["--no-sandbox", "--disable-dev-shm-usage", "--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"], slow_mo=200, channel="chromium")

    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    user_email = generate_email()

    # Step 1: Open the Expensify URL
    page.goto('https://dev.new.expensify.com:8082/')

    # Step 2: Enter a generated email and click continue
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(1000)

    # Step 3: Click the join button if available, otherwise skip
    try:
        page.locator('button[tabindex="0"]').click()
        page.wait_for_timeout(1000)
    except Exception:
        pass

    # Step 4: Ensure that the user reaches the dashboard by checking for visible text
    expect(page.locator("text=What do you want to do today?")).to_be_visible()

    # Step 5: Select 'Track and budget expenses' in the onboarding page and click Continue
    page.locator("text='Track and budget expenses'").click()
    page.wait_for_timeout(1000)

    # Step 6: Enter first name, last name, and continue
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()
    page.wait_for_timeout(1000)

    return browser, page


def test_multiple_selector_in_workspace():
    with sync_playwright() as p:
        # A list to store any assertion failures so we can print them at the end
        errors = []

        # Step 1: Login user
        browser, page = login_user(p)
        context = page.context
        # Start tracing
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        
        try:
            # Navigate to Workspaces settings
            page.get_by_label("My settings").click()
            page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").get_by_text("Workspaces").click()
            page.get_by_label("New workspace").click()
            page.get_by_text("More features").click()
            page.get_by_label("Classify costs and track").click()
            page.get_by_label("Document and reclaim eligible").click()
            page.get_by_label("Set up custom fields for").click()
            page.get_by_role("button", name="Upgrade").click()
            page.wait_for_timeout(1000)
            page.get_by_role("button", name="Got it, thanks").click()

            # --- Categories Section ---
            page.get_by_test_id("WorkspaceInitialPage").get_by_text("Categories").click()
            page.locator("#Benefits").get_by_label("Benefits").click()
            page.wait_for_timeout(1000)
            page.locator("#Advertising").get_by_label("Advertising").click()
            page.wait_for_timeout(1000)
            page.locator("#Car").get_by_label("Car").click()
            assert page.get_by_role("button", name="selected").is_visible()
            # Check button is green
            button_locator = page.get_by_role("button", name="selected")

            # Evaluate the element's inline style for backgroundColor
            actual_bg_color = button_locator.evaluate("el => el.style.backgroundColor")

            # Assert or compare with the expected value
            try:
                # If the element truly has inline style: background-color: rgb(3, 212, 124);
                # you should see "rgb(3, 212, 124)" in actual_bg_color.
                assert actual_bg_color == "rgb(3, 212, 124)", (
                    f"Expected inline backgroundColor to be 'rgb(3, 212, 124)' in Categories, "
                    f"but got '{actual_bg_color}'\n"
                )
            except AssertionError as e:
                errors.append(str(e))
            page.wait_for_timeout(1000)

            # --- Tags Section ---
            page.get_by_test_id("WorkspaceInitialPage").get_by_text("Tags").click()
            page.get_by_role("button", name="Add tag").click()
            page.get_by_role("textbox", name="Name").fill("To pay")
            page.get_by_role("button", name="Save").click()
            page.locator("button").filter(has_text="To payEnabled").get_by_label("To pay").click()
            # Check button is green
            button_locator = page.get_by_role("button", name="selected")

            # Evaluate the element's inline style for backgroundColor
            actual_bg_color = button_locator.evaluate("el => el.style.backgroundColor")

            # Assert or compare with the expected value
            try:
                # If the element truly has inline style: background-color: rgb(3, 212, 124);
                # you should see "rgb(3, 212, 124)" in actual_bg_color.
                assert actual_bg_color == "rgb(3, 212, 124)", (
                    f"Expected inline backgroundColor to be 'rgb(3, 212, 124)' in Tags, "
                    f"but got '{actual_bg_color}'\n"
                )
            except AssertionError as e:
                errors.append(str(e))
            page.wait_for_timeout(1000)

            # --- Taxes Section ---
            page.get_by_test_id("WorkspaceInitialPage").get_by_text("Taxes").click()
            page.locator("#id_TAX_RATE_1").get_by_label("Tax Rate").click()
            # Check button is green
            button_locator = page.get_by_role("button", name="selected")

            # Evaluate the element's inline style for backgroundColor
            actual_bg_color = button_locator.evaluate("el => el.style.backgroundColor")

            # Assert or compare with the expected value
            try:
                # If the element truly has inline style: background-color: rgb(3, 212, 124);
                # you should see "rgb(3, 212, 124)" in actual_bg_color.
                assert actual_bg_color == "rgb(3, 212, 124)", (
                    f"Expected inline backgroundColor to be 'rgb(3, 212, 124)' in Taxes, "
                    f"but got '{actual_bg_color}'\n"
                )
            except AssertionError as e:
                errors.append(str(e))
            page.wait_for_timeout(1000)

            # --- Report Fields Section ---
            page.get_by_test_id("WorkspaceInitialPage").get_by_text("Report fields").click()
            page.get_by_role("button", name="Add field").click()
            page.get_by_test_id("CreateReportFieldsPage").get_by_text("Name").click()
            page.get_by_role("textbox", name="Name").fill("to pay")
            page.get_by_test_id("TextSelectorModal").get_by_role("button", name="Save").click()
            page.get_by_test_id("CreateReportFieldsPage").get_by_text("Type").click()
            page.get_by_label("Text").click()
            page.get_by_text("Initial value").click()
            page.get_by_role("textbox", name="Initial value").fill("none")
            page.get_by_test_id("TextSelectorModal").get_by_role("button", name="Save").click()
            page.get_by_role("button", name="Save").nth(0).click()
            page.locator("#field_id_TO_PAY").get_by_label("to pay").click()
            # Check button is green
            button_locator = page.get_by_role("button", name="selected")

            # Evaluate the element's inline style for backgroundColor
            actual_bg_color = button_locator.evaluate("el => el.style.backgroundColor")

            # Assert or compare with the expected value
            try:
                # If the element truly has inline style: background-color: rgb(3, 212, 124);
                # you should see "rgb(3, 212, 124)" in actual_bg_color.
                assert actual_bg_color == "rgb(3, 212, 124)", (
                    f"Expected inline backgroundColor to be 'rgb(3, 212, 124)' in Reports fields, "
                    f"but got '{actual_bg_color}'\n"
                )
            except AssertionError as e:
                errors.append(str(e))
            page.wait_for_timeout(1000)

            assert not errors, "\n".join(errors)

        finally:
            # Stop tracing and export the trace file
            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            context.tracing.stop(path=trace_path)
            trace_cleaner(trace_path)
            browser.close()


if __name__ == '__main__':
    test_multiple_selector_in_workspace()
