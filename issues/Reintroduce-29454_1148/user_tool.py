import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from utils.trace_cleaner import trace_cleaner

GMAIL_NAME = "nomandevtur+2945477"
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
    
    page.get_by_role("textbox", name="Phone or email").fill(user_info["email"])
    page.locator("div:nth-child(3) > div:nth-child(2) > div > div").first.click()

    magic_code = "134907"
    page.wait_for_timeout(3000)

    validate_code_input = page.locator('input[name="validateCode"]').first
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
    
def test_delete_saved_search():
    with sync_playwright() as p:
        user_info = get_test_user_info()
        browser, context, page = launch_app(p)
        # Start tracing
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        try:
            login_user(page, user_info)

            # Turn off the internet
            context.set_offline(True)
            print("Internet turned off")
            page.wait_for_timeout(2000)
            page.locator('div[aria-label="My settings"]').click()
            page.wait_for_timeout(1000)
            page.get_by_label("Workspaces").click()
            page.wait_for_timeout(1000)
            page.get_by_label("New workspace").click()
            page.wait_for_timeout(1000)
            page.get_by_test_id("WorkspaceInitialPage").get_by_label("Back").click()
            page.wait_for_timeout(1000)
            page.get_by_label("Back").nth(1).click()
            page.wait_for_timeout(1000)
            page.get_by_label("Back").first.click()
            page.wait_for_timeout(1000)
            page.get_by_text("#admins").click()
            page.wait_for_timeout(1000)
            page.get_by_role("textbox", name="Write something...").click()
            page.get_by_role("textbox", name="Write something...").fill("colab and dont need assistance")
            page.keyboard.press("Enter")   
            page.wait_for_timeout(1000)
            page.get_by_label("#admins").get_by_text("#admins").click()
            page.wait_for_timeout(1000)
            page.get_by_test_id("ReportDetailsPage").get_by_label("Settings").click()
            page.wait_for_timeout(1000)

            # Check if the div containing the text "Welcome message" is present
            locator = page.locator('div:has-text("Welcome message")')

            # Assert that the div is present
            assert locator.count() > 0, "Welcome message is not visible on admin "

            page.get_by_label("Close").nth(1).click()
            page.wait_for_timeout(1000)
            page.locator("span:has-text('colab and dont need assistance')").hover()
            page.wait_for_timeout(1000)
            page.get_by_test_id("SvgChatbubble Icon").locator("path").click()
            page.wait_for_timeout(1000)
            page.get_by_label("colab and dont need assistance").get_by_text("colab and dont need assistance").click()
            page.wait_for_timeout(1000)
            page.get_by_test_id("ReportDetailsPage").get_by_label("Settings").click()
            page.wait_for_timeout(1000)

            # Check if the div containing the text "Welcome message" is present
            locator = page.locator('div:has-text("Welcome message")')

            # Assert that the div is not present
            assert locator.count() < 1, "Welcome message is visible on thread "

            page.wait_for_timeout(5000)
        except Exception as e:
            raise e
        finally:
            # Stop tracing and save the trace
            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            # Clean the trace
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            context.close()
            browser.close()
