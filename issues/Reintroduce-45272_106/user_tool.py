import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright
from utils.trace_cleaner import trace_cleaner

user_email = "totherandomuser@gmail.com"
password = "umei djwi bfmp jntm"

def login(p, if_phone=False, first_name="John", last_name="Cena"):
    # step 1: Login
    permissions = ['clipboard-read', 'clipboard-write']
    browser = p.chromium.launch(headless=True, slow_mo=1000, args=["--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"], proxy = {"server":"http://localhost:8080"})

    if if_phone:
        phone = p.devices['iPhone 12 Pro']
        context = browser.new_context(**phone, permissions=permissions, reduced_motion='no-preference')
    else:
        context = browser.new_context()

    page = context.new_page()

    page.goto('https://dev.new.expensify.com:8082/') 

    phone_or_email_input = page.locator('input[type="email"]')
    phone_or_email_input.fill(user_email)

    continue_button = page.locator('button[tabindex="0"]')
    continue_button.click()

    magic_code = "123456"

    validate_code_input = page.locator('input[name="validateCode"]')
    validate_code_input.fill(magic_code)

    return browser, page, context


def test():
    with sync_playwright() as p:
        browser, page, context = login(p, True)

        context.tracing.start(title="Output Browser 1", screenshots=True, snapshots=True)

        try:
            # Step 1: Login is already done in login function
            # Step 2: Navigate and perform actions
            page.get_by_label("My settings").click()
            page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").get_by_text("Workspaces").click()
            page.locator("button").filter(has_text="Deepak Dhaka's Workspace.").click()
            page.get_by_text("More features").click()

            # Locate the toggle button by aria-label
            toggle_button = page.get_by_role("switch", name="Gain insights and control over spend")
            # Check if the button is already in the "on" state by inspecting aria-checked
            is_on = toggle_button.get_attribute("aria-checked") == "true"
            if not is_on:
                toggle_button.click()
                print("Button was off, now turned on.")
            else:
                print("Button is already on; clicking twice!!")
                toggle_button.click()
                toggle_button.click()

            page.get_by_text("Expensify Card").click()
            page.get_by_role("button", name="Issue card").click()
            page.get_by_label("Deepak Dhaka").click()

            # set offline and check for the text position
            text_to_find = "You appear to be offline."
            elements = page.locator(f"text={text_to_find}")
            context.set_offline(True)

            # Iterate through each element and print its position
            y_pos = []
            count = elements.count()
            if count > 0:
                for i in range(count):
                    bounding_box = elements.nth(i).bounding_box()
                    if bounding_box:
                        print(f"Element {i+1} position: {bounding_box}")
                        y_pos.append(bounding_box['y'])

            assert 361 not in y_pos, "You appear to be offline, has been found at an unusual location."

        except Exception as e:
            raise e
        finally:
            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            context.tracing.stop(path=trace_path)
            trace_cleaner(trace_path)
            browser.close()
            context.close()
