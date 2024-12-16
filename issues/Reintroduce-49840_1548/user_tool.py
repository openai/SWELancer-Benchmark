import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import re
from playwright.sync_api import sync_playwright
from utils.trace_cleaner import trace_cleaner


# Generate a random email
def generate_random_email():
    username = "jellystarfish99"
    test_email = f"{username}+{49840}+{449840}@gmail.com"
    return test_email


def login_user(page, first_name="test"):
    user_email = generate_random_email()

    # Step 1: Open expensify url
    page.goto('https://dev.new.expensify.com:8082/', timeout=60000)

    # Step 2: Enter email and click continue
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(1000)

    # Step 3: Click join button
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(1000)

    try:
        # Step 4: Select 'Track and budget expenses' in onboarding page and click Continue
        page.locator("text='Track and budget expenses'").click()
        page.get_by_role("button", name="Continue").click()
        page.wait_for_timeout(1000)

        # Step 5: Enter first name, last name and click continue
        page.locator('input[name="fname"]').fill(first_name)
        page.get_by_role("button", name="Continue").last.click()
        page.wait_for_timeout(1000)
    except:
        pass

    return user_email


def submit_expense_in_workspace_chat(page, workspace_name, user_email, amount="10"):
    page.wait_for_timeout(2000)
    # Step 1: Click on workspace chat
    page.get_by_label("Iniciar chat (Acción flotante)").click()
    page.get_by_label("Presentar gasto").first.click()
    page.wait_for_timeout(1000)

    # Step 2: Click on "Manual" button and enter amount
    manual_button = page.locator('button[aria-label="Manual"]')
    manual_button.click()
    page.wait_for_timeout(1000)

    page.locator('input[role="presentation"]').fill(amount)

    # Step 4: Click on Next button
    next_button = page.locator('button[data-listener="Enter"]', has_text="Siguiente").first
    next_button.click()
    page.wait_for_timeout(1000)

    page.get_by_test_id("selection-list-text-input").fill(workspace_name)
    page.wait_for_timeout(2000)
    page.get_by_label(workspace_name).last.click()

    # Step 5: Add merchant details
    merchant_field = page.locator('div[role="menuitem"]', has_text="Comerciante")
    merchant_field.click()
    page.wait_for_timeout(1000)

    page.locator('input[aria-label="Comerciante"]').fill("Self")

    save_button = page.locator('button', has_text="Guardar")
    save_button.click()
    page.wait_for_timeout(1000)

    # Step 6: Submit the expense
    save_button = page.locator('button[data-listener="Enter"]', has_text="Solicitar")
    save_button.click()
    page.wait_for_timeout(1000)


def test_save_description_in_submitted_expense():
    with sync_playwright() as p:
        browser = None
        context = None
        try:
            # Create browser/context and start tracing
            browser = p.chromium.launch(headless=True, args=[
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
            ])
            context = browser.new_context()
            context.tracing.start(screenshots=True, snapshots=True, sources=True)
            page = context.new_page()

            # Step 1: Log in user
            user_email = login_user(page)

            # Step 2: Create a new workspace
            random_int_1 = 49
            random_int_2 = 840
            workspace_name = f"WS-{random_int_1}{random_int_2}"
            page.get_by_label("My settings").click()
            page.wait_for_timeout(2000)
            page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()
            page.wait_for_timeout(2000)
            page.get_by_role("button", name="New workspace").first.click()
            page.wait_for_timeout(2000)

            page.get_by_test_id("WorkspacePageWithSections").get_by_text("Name").click()
            page.wait_for_timeout(1000)
            page.get_by_role("textbox", name="Name").press("ControlOrMeta+a")
            page.wait_for_timeout(1000)
            page.get_by_role("textbox", name="Name").fill(workspace_name)
            page.wait_for_timeout(1000)
            page.get_by_role("button", name="Save").click()
            page.wait_for_timeout(1000)

            # Step 3: Click on Back arrow to go back and navigate to inbox screen
            back_arrow_button = page.locator('button[aria-label="Back"]')
            back_arrow_button.click()

            # Step 4: Change the language
            preference_button = page.locator('div[aria-label="Preferences"]')
            preference_button.click()

            get_language = page.locator('div[aria-label="English"][tabindex="0"]')
            get_language.click()
            page.wait_for_timeout(1000)

            page.locator('button[aria-label="Spanish"][tabindex="0"]').click()

            inbox_menu = page.locator('button[aria-label="Recibidos"]')
            inbox_menu.click()
            page.wait_for_timeout(2000)

            # Step 5: Submit an expense in workspace chat
            submit_expense_in_workspace_chat(page, workspace_name, user_email)

            # Step 6: Choose elsewhere pay option and select
            choose_pay_option = page.get_by_label("Ver detalles").get_by_role("button").nth(1)
            choose_pay_option.click()
            page.wait_for_timeout(1000)

            pattern = re.compile(r"Pagar .+ de otra forma$")
            find_option = page.locator(f"text=/{pattern.pattern}/")
            find_option.click()
            page.wait_for_timeout(1000)

            pay_button = page.locator(f"text=/{pattern.pattern}/")
            pay_button.click()

            assert page.get_by_text("Pago Completo").is_visible()

        except Exception as e:
            # Ensure the trace is still saved if there is a test failure
            raise e
        finally:
            if context:
                context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
                trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            if browser:
                browser.close()
