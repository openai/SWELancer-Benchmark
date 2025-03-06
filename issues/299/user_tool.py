import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import os
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from utils.trace_cleaner import trace_cleaner


GMAIL_NAME = "nomandevtur+41183"
GMAIL_APP_PASSWORD = ""


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

        expect(page.get_by_label("Inbox")).to_be_visible(timeout=10000)
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
    context = browser.new_context(**context_args)
    page = context.new_page()
    return browser, context, page


def get_context(p: PlaywrightContextManager, user_info, browser, is_phone_setup=False):
    permissions = ['clipboard-read', 'clipboard-write']

    data_dir = 'desktop_context' if is_phone_setup else 'mobile_context'
    data_dir += f"_{user_info['email']}"
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    context_options = {}

    if is_phone_setup:
        context_options = p.devices['iPhone 12 Pro']

    context = p.chromium.launch_persistent_context(
        data_dir,
        slow_mo=1000,
        headless=True,
        **context_options,
        permissions=permissions,
        reduced_motion='no-preference'
    )

    return context, context.pages[0]


def test_text_what_would_you_like_to_do_with_this_expense():
    with sync_playwright() as p:
        browser, context, page = launch_app(p)

        context.tracing.start(title="output_browser1", snapshots=True, screenshots=True)
        try:
            user_info = get_test_user_info()

            login_user(page, user_info)


            page.wait_for_timeout(3000)
            page.get_by_test_id("4621203041582643").click()

            page.wait_for_timeout(3000)

            screen_id = page.url.split('/')[-1]
            page.get_by_test_id(f"report-screen-{screen_id}").get_by_label("Create").click()
            page.get_by_label("Track expense").click()
            page.get_by_label("Manual").click()
            page.get_by_placeholder("0").fill("100")
            page.locator("#numPadContainerView").get_by_role("button", name="Next").click()
            page.get_by_role("button", name="Track expense").click()
            page.get_by_role("button", name="Submit it to someone").last.click()
            page.get_by_test_id("selection-list-text-input").fill("expensifyolddot@gmail.com")
            page.wait_for_timeout(3000)
            page.get_by_label("expensifyolddot@gmail.com").click()
            page.get_by_role("button", name="Submit PKR").click()

            page.wait_for_timeout(5000)
            locator = page.locator('div:has-text("What would you like to do with this expense?")')


            assert locator.count() < 1, "Text \"What would you like to do with this expense?\" is visible"

            print("Text \"What would you like to do with this expense? \" is not visible")

        except Exception as e:
            raise e
        finally:

            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            context.tracing.stop(path=trace_path)
            trace_cleaner(trace_path)
            browser.close()
}