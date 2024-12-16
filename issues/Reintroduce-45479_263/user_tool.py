import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from utils.trace_cleaner import trace_cleaner

# Utility to generate a random email
def generate_random_email():
    postfix = 1734007944
    return f"testuserexpensify+{postfix}@gmail.com"

def test():
    with sync_playwright() as p:
        # We'll record tracing in one context and save it in a finally block.
        browser = None
        context = None
        try:
            # Launch the browser
            browser = p.chromium.launch(
                headless=True, slow_mo=1000,
                args=["--ignore-certificate-errors", 
                      "--disable-web-security", 
                      "--disable-features=IsolateOrigins,site-per-process"]
            )

            # Create a context so we can record a trace
            context = browser.new_context()
            context.tracing.start(screenshots=True, snapshots=True, sources=True)

            # Open a new page, then proceed with the test steps.
            page = context.new_page()

            # Generate email and go to Expensify
            user_email = generate_random_email()
            page.goto('https://dev.new.expensify.com:8082/')

            # Enter email and click continue
            page.locator('input[type="email"]').fill(user_email)
            page.locator('button[tabindex="0"]').click()
            page.wait_for_timeout(1000)

            # Click join button
            try:
                page.locator('button[tabindex="0"]').click()
                page.wait_for_timeout(1000)
            except Exception:
                pass
            expect(page.locator("text=What do you want to do today?")) .to_be_visible()

            # Select 'Track and budget expenses' on first onboarding page
            page.locator("text='Track and budget expenses'").click()
            page.get_by_role("button", name="Continue").click()
            page.wait_for_timeout(1000)

            # Enter first name, last name and click continue
            first_name = "John"
            last_name = "Doe"
            page.locator('input[name="fname"]').fill(first_name)
            page.locator('input[name="lname"]').fill(last_name)
            page.get_by_role("button", name="Continue").last.click()
            page.wait_for_timeout(1000)

            # The rest of the test steps
            page.wait_for_timeout(1000)
            click_settings_button = page.locator("[aria-label='My settings']")
            click_settings_button.click()
            page.wait_for_timeout(1000)

            click_workspace_button = page.locator("div[aria-label='Workspaces']")
            click_workspace_button.click()
            page.wait_for_timeout(1000)

            create_new_workspace_button = page.locator("[aria-label='New workspace']").nth(0)
            create_new_workspace_button.click()
            page.wait_for_timeout(1000)

            currency_divs = page.locator('div[aria-label*="-"]')
            currency_divs.click()
            page.wait_for_timeout(1000)

            click_aud_currency_button = page.locator("[aria-label='AUD - A$']")
            click_aud_currency_button.click()
            page.wait_for_timeout(1000)

            click_more_features = page.locator("[aria-label='More features']")
            click_more_features.click()
            page.wait_for_timeout(1000)

            enable_distance_rates = page.locator("button[aria-label='Add, update, and enforce rates.']")
            enable_distance_rates.click()
            page.wait_for_timeout(1000)

            click_distance_rates = page.locator("div[aria-label='Distance rates']")
            click_distance_rates.click()
            page.wait_for_timeout(1000)

            select_existing_distance = page.locator("div", has_text="Enabled").nth(-1)
            select_existing_distance.click()
            page.wait_for_timeout(1000)

            click_rate = page.locator("div", has_text="Rate").nth(-1)
            click_rate.click()
            page.wait_for_timeout(1000)

            page.locator('input[type="text"]').fill("1")

            click_save = page.locator("div", has_text="Save").nth(-1)
            click_save.click()
            page.wait_for_timeout(1000)

            click_back_button = page.locator("[aria-label='Back']").nth(-1)
            click_back_button.click()
            page.wait_for_timeout(1000)

            click_back_button = page.locator("[aria-label='Back']").nth(-1)
            click_back_button.click()
            page.wait_for_timeout(1000)

            # Second workspace creation
            create_new_workspace_button = page.locator("[aria-label='New workspace']").nth(0)
            create_new_workspace_button.click()
            page.wait_for_timeout(1000)

            currency_divs = page.locator('div[aria-label*="-"]')
            currency_divs.click()
            page.wait_for_timeout(1000)

            click_aud_currency_button = page.locator("[aria-label='AUD - A$']")
            click_aud_currency_button.click()
            page.wait_for_timeout(1000)

            click_more_features = page.locator("[aria-label='More features']")
            click_more_features.click()
            page.wait_for_timeout(1000)

            enable_distance_rates = page.locator("button[aria-label='Add, update, and enforce rates.']")
            enable_distance_rates.click()
            page.wait_for_timeout(1000)

            click_distance_rates = page.locator("div[aria-label='Distance rates']")
            click_distance_rates.click()
            page.wait_for_timeout(1000)

            select_existing_distance = page.locator("div", has_text="Enabled").nth(-1)
            select_existing_distance.click()
            page.wait_for_timeout(1000)

            click_rate = page.locator("div", has_text="Rate").nth(-1)
            click_rate.click()
            page.wait_for_timeout(1000)

            page.locator('input[type="text"]').fill("2")

            click_save = page.locator("div", has_text="Save").nth(-1)
            click_save.click()
            page.wait_for_timeout(1000)

            click_back_button = page.locator("[aria-label='Back']").nth(-1)
            click_back_button.click()
            page.wait_for_timeout(1000)

            click_back_button = page.locator("[aria-label='Back']").nth(-1)
            click_back_button.click()
            page.wait_for_timeout(1000)

            # Click Inbox button
            click_start_chat = page.locator('[aria-label="Start chat (Floating action)"]')
            click_start_chat.click()
            page.wait_for_timeout(1000)

            click_submit_expense_button = page.locator("[aria-label='Submit expense']")
            click_submit_expense_button.click()
            page.wait_for_timeout(1000)

            click_distance = page.locator('[aria-label="Distance"]')
            click_distance.click()
            page.wait_for_timeout(1000)

            click_start = page.locator('div[data-rbd-draggable-id="start_waypointwaypoint0"]')
            click_start.click()
            page.wait_for_timeout(1000)

            page.locator('input[rows="1"]').fill("est")
            page.wait_for_timeout(3000)

            select_first_address = page.locator('div[id="result-list-id"]').locator(
                'div', has_text="Estes Park").nth(0)
            select_first_address.click()
            page.wait_for_timeout(1000)

            click_stop = page.locator('div[data-rbd-draggable-id="stop_waypointwaypoint1"]')
            click_stop.click()
            page.wait_for_timeout(1000)

            page.locator('input[rows="1"]').fill("aur")
            page.wait_for_timeout(3000)

            select_first_address = page.locator('div[id="result-list-id"]').locator(
                'div', has_text="Aurora").nth(0)
            select_first_address.click()
            page.wait_for_timeout(5000)

            click_next = page.locator("div", has_text="Next").nth(-1)
            click_next.click()
            page.wait_for_timeout(2000)

            # Select first workspace
            click_first_workspace = page.locator(
                f'button[aria-label="{first_name.capitalize()} {last_name}\'s Workspace"]')
            click_first_workspace.click()
            page.wait_for_timeout(2000)

            first_currency_text = page.locator('div', has_text="A$").nth(-1).text_content()
            page.wait_for_timeout(1000)

            click_back_button = page.locator("[aria-label='Back']").nth(-1)
            click_back_button.click()
            page.wait_for_timeout(1000)

            click_second_workspace = page.locator(
                f'button[aria-label="{first_name.capitalize()} {last_name}\'s Workspace 1"]')
            click_second_workspace.click()
            page.wait_for_timeout(1000)

            second_currency_text = page.locator('div', has_text="A$").nth(-1).text_content()
            page.wait_for_timeout(1000)

            # Assert that the two text values are not equal
            assert first_currency_text.strip().lower() != second_currency_text.strip().lower(), "The two currency texts should not be equal."
        except Exception as e:
            # Re-raise so the test fails, but we still save the trace in the finally block
            raise e
        finally:
            # Stop and save the trace, then clean it
            if context:
                context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
                trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            if browser:
                browser.close()
