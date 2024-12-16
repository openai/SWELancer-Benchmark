import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import Playwright, sync_playwright, expect

def generate_random_email():
    return f"bobexpensifytest+49993o@gmail.com"


def test_track_expense_rate(playwright: Playwright) -> None:
    email = generate_random_email()
    first_name = 's'
    last_name = 's'

    browser = playwright.chromium.launch(channel="chrome", headless=True, slow_mo=1000, args=[
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ])
    context = browser.new_context(viewport={"width":1000,"height":550})
    page = context.new_page()

    page.goto("https://dev.new.expensify.com:8082/")
    # Step 2: Enter email and click continue
    page.locator('input[type="email"]').fill(email)
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(1000)

    # Step 3: Click join button
    page.get_by_role("button", name="Join").click()

    # Step 4: Select 'Track and budget expenses' in onboarding page and click Continue
    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()
    page.wait_for_timeout(1000)

    # Step 5: Enter first name, last name and click continue
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()

    page.wait_for_timeout(1000)
    page.wait_for_timeout(500) 
    page.locator('button[aria-label="My settings"]').click()
    page.wait_for_timeout(500)  # Short delay
    

    page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").get_by_text("Workspaces").click()
    page.get_by_label("New workspace").first.click()
    page.wait_for_timeout(500)  # Short delay
    page.get_by_label("Back").click()
    page.locator('button[aria-label="Inbox"]').click()
    page.locator('button[aria-label="Create"]').click()

    page.get_by_text("Submit expense", exact=True).click()
    page.get_by_label("Manual").click()
    page.get_by_placeholder("0").fill("100")
    page.locator("#numPadContainerView").get_by_role("button", name="Next").click()
    page.get_by_text("Description").click()
    page.get_by_role("textbox", name="What's it for?").fill("descrip")
    page.get_by_role("button", name="Save").click()
    page.get_by_text("Merchant").click()
    page.get_by_role("textbox", name="Merchant").fill("ABC")
    page.get_by_role("button", name="Save").click()
    page.locator('button[data-listener="Enter"]', has_text="Submit").click()
    check_text = page.locator('div[aria-label="Last chat message preview"]').nth(2).text_content()
    assert "ABC" in check_text, "The merchant 'ABC' is not in the check text."

    # Close the browser
    browser.close()

