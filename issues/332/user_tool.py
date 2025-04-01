import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from utils.trace_cleaner import trace_cleaner

GMAIL_NAME = "nomandevtur+29433"
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
    

    page.get_by_label(activity_text).click()


    page.get_by_role("textbox", name="First name").fill(first_name)
    page.get_by_role("textbox", name="Last name").fill(last_name)
    page.get_by_role("button", name="Continue").last.click()


def login_user(page, user_info, activity_text="Track and budget expenses"):

    page.context.clear_cookies()

    page.goto('https://dev.new.expensify.com:8082/')
    page.wait_for_load_state('load')
    
    try:

        expect(page.get_by_label("Inbox")).to_be_visible(timeout=3000)
        return
    except:
        pass

    page.get_by_test_id("username").fill(user_info["email"])
    page.get_by_role("button", name="Continue").click()

    join_button = page.get_by_role("button", name="Join")
    validate_code_input = page.locator('input[data-testid="validateCode"]')
    expect(join_button.or_(validate_code_input)).to_be_visible()

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
    context = browser.new_context(**context_args, permissions=[])
    page = context.new_page()
    return browser, context, page
    
def test_book_travel_report_screen():
    with sync_playwright() as p:
        browser, context, page = launch_app(p)

        context.tracing.start(
            title="test_book_travel_report_screen",
            screenshots=True,
            snapshots=True,
            sources=True
        )
        
        try:
            user_info = get_test_user_info(first_name="abc", last_name="abc")
            login_user(page, user_info)

            page.wait_for_timeout(3000)


            page.get_by_label("Start chat (Floating action)").click()
            page.get_by_label("Submit expense").click()


            page.get_by_label("Distance").click()
            page.get_by_test_id("IOURequestStartPage").get_by_role("button", name="Start").click()
            page.get_by_label("Use current location").click()
            page.get_by_test_id("IOURequestStepWaypoint").get_by_role("textbox").click()
            page.get_by_test_id("IOURequestStepWaypoint").get_by_role("textbox").fill("Karachi")
            page.wait_for_timeout(3000)


            page.get_by_test_id("IOURequestStepWaypoint").get_by_label("Close").click()


            locator = page.locator('span:has-text("It looks like you\'ve denied access to your location. Please")')


            assert locator.count() == 0, "The span with the text 'It looks like you've denied access to your location. Please' is found."

            print("The message 'It looks like you've denied access to your location. Please allow location' is not visible on page")

            page.wait_for_timeout(2000)
        except Exception as e:
            print(f"An exception occurred: {e}")
            raise
        finally:

            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            context.close()
            browser.close()
