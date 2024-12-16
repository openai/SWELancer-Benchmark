import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect

GMAIL_NAME = "nomandevtur+27363"
GMAIL_APP_PASSWORD = "tpye xlsj axyq nltq"


def get_test_user_info(seed = None, first_name = None, last_name = None):
    if first_name is None:
        first_name = GMAIL_NAME

    if last_name is None:
        last_name = ""

    email = f"{GMAIL_NAME}+{seed}@gmail.com" if seed is not None else f"{GMAIL_NAME}@gmail.com"
    
    return {"email": email, "password": GMAIL_APP_PASSWORD, "first_name": first_name, "last_name": last_name}



def select_activity(page, first_name, last_name, activity_text):
    expect(page.get_by_text("What do you want to do today?")).to_be_visible()
    
    # Select activity in onboarding page and click Continue
    page.get_by_label(activity_text).click()

    # Enter first name, last name and click continue
    page.get_by_role("textbox", name="First name").fill(first_name)
    page.get_by_role("textbox", name="Last name").fill(last_name)
    page.get_by_role("button", name="Continue").last.click()


def login_user(page, user_info, activity_text="Track and budget expenses"):
    # Clear cookies, local storage, and session storage
    page.context.clear_cookies()

    page.goto('https://dev.new.expensify.com:8082/')
    page.wait_for_load_state('load')
    
    try:
        # If the user is already logged in, the inbox should be visible
        expect(page.get_by_label("Inbox")).to_be_visible(timeout=3000)
        return
    except:
        pass

    page.get_by_test_id("username").fill(user_info["email"])
    page.get_by_role("button", name="Continue").click()

    join_button = page.get_by_role("button", name="Join")
    validate_code_input = page.locator('input[data-testid="validateCode"]')

    if (join_button.is_visible()):
        join_button.click(timeout=3000)
    else:
        magic_code = "123456"
        print(f"Magic code: {magic_code}")
        validate_code_input.fill(magic_code)

    page.wait_for_timeout(3000)

    select_activity_dialog = page.get_by_text("What do you want to do today?")
    if select_activity_dialog.count() > 0:
        select_activity(page, user_info["first_name"], user_info["last_name"], activity_text)


def launch_app(pw, headless=True, device=None, geolocation=None):
    browser = pw.chromium.launch(headless=headless, slow_mo=500, args=[
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ],
    )
    context_args = {"viewport": {"width": 1024, "height": 640}}
    if device:
        context_args.update(pw.devices[device])
    if geolocation:
        context_args["geolocation"] = geolocation
        context_args["permissions"] = ["geolocation"]
    context = browser.new_context(**context_args)
    page = context.new_page()
    return browser, context, page
    
def test_assign_share_url():
    with sync_playwright() as p:
        
        user_info = get_test_user_info(first_name="abc", last_name="abc")

        browser, context, page = launch_app(p)
        login_user(page, user_info)

        page.wait_for_timeout(3000)

        # move to personal chat
        locator = page.locator(f"span:has-text('random email (you)')").click()

        page.wait_for_timeout(1000)
        screen_id = page.url.split('/')[-1]

        page.get_by_test_id(f"report-screen-{screen_id}").get_by_label("Create").click()
        page.get_by_label("Assign task").click()
        page.get_by_role("textbox", name="Title").fill("task99")
        page.get_by_role("button", name="Next").click()
        page.get_by_test_id("NewTaskPage").get_by_label("Back").click()
        page.wait_for_timeout(1000)
        page.get_by_label("Back").click()
        page.wait_for_timeout(1000)
        page.get_by_role("textbox").fill("https://dev.new.expensify.com:8082/new/task/somewhere11")

        page.get_by_test_id(f"report-screen-{screen_id}").get_by_label("Send").click()
        page.get_by_test_id(f"report-screen-{screen_id}").get_by_test_id("report-actions-list").get_by_text("https://dev.new.expensify.com:8082/new/task/somewhere11").click()
        page.wait_for_timeout(3000)

        # Check if the div containing the text "Hmm... it's not here" is present
        locator = page.locator('div:has-text("Hmm... it\'s not here")')

        # Assert that the div is present
        assert locator.count() > 0, "The div with the text 'Hmm... it's not here' is not found."

        print("The message 'Hmm... it's not here' is visible on page")

        page.wait_for_timeout(4000)
        page.close()
        browser.close()


