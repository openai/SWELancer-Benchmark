import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright


user_email = "totherandomuser+005@gmail.com"
password = "umei djwi bfmp jntm"


def get_magic_code(user_email, password, retries=5, delay=5):
    default_otp_code = "123456"
    return default_otp_code


def login(p, if_phone=False, first_name="John", last_name="Cena"):
    
    # step 1: Login
    permissions = ['clipboard-read', 'clipboard-write']
    browser = p.chromium.launch(headless=True, args=[
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
        ])

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

    page.wait_for_timeout(1000)

    magic_code = get_magic_code(user_email, password, retries=3, delay=10)

    validate_code_input = page.locator('input[name="validateCode"]')
    validate_code_input.fill(magic_code)

    page.wait_for_timeout(1000)

    return browser, page, context


def test():
    with sync_playwright() as p:

        # Step 1: Login
        browser, page, context = login(p, False)

        # Step 2: Create Workspace
        random_int_1 = 23
        random_int_2 = 21
        workspace_name =  f"WS-{random_int_1}{random_int_2}"
        room_name =  f"r-{random_int_1}{random_int_2}"
        email_1 = f"dev091197+{random_int_1}+{random_int_2}@gmail.com"
        test_name = "test inzi"
        page.get_by_label("My settings").click()
        page.wait_for_timeout(2000)
        page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()
        page.get_by_role("button", name="New workspace").first.click()
        page.wait_for_timeout(1000)
        page.get_by_test_id("WorkspacePageWithSections").get_by_text("Name").click()
        page.wait_for_timeout(1000)
        page.get_by_role("textbox", name="Name").press("ControlOrMeta+a")
        page.wait_for_timeout(1000)
        page.get_by_role("textbox", name="Name").fill(workspace_name)
        page.wait_for_timeout(1000)
        page.get_by_role("button", name="Save").click()
        page.wait_for_timeout(1000)
        page.get_by_label("Back").click()
        page.get_by_label("Inbox").click()

        # create a new task and add the title
        page.get_by_label("Create").last.click()
        page.get_by_text("Assign task").click()
        page.get_by_role("textbox", name="Title").click()
        page.get_by_role("textbox", name="Title").fill("hello")
        page.get_by_role("button", name="Next").click()

        # copy the link and open this link in a new tab
        old_url = page.url
        second_tab = context.new_page()
        second_tab.goto(old_url)

        # switch the tab again
        second_tab.keyboard.down("Control")  # Press down the Control key
        second_tab.keyboard.press("Tab")     # Press Tab while Control is down
        second_tab.keyboard.up("Control")    # Release the Control key
        page.get_by_role("button", name="Confirm task").click()

        # look for hello
        hello_container = page.locator("div[aria-label='hello'][role='menuitem']")
        hello_container_count = hello_container.count()
        
        assert hello_container_count == 0, "The count should be 0, but it is not."