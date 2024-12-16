import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect

# Expensify app URL
EXPENSIFY_URL = "https://dev.new.expensify.com:8082/"

# Email for login
EMAIL = "naturesv057+44194_1@gmail.com"

def launch_browser(pw, device=None, geolocation=None):
    """
    Launch the browser.
    """
    browser = pw.chromium.launch(
        headless=True,
        proxy={
            'server': 'http://127.0.0.1:8080',  
        },
        args=[
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
        ],
        slow_mo=1000
    )
    context_args = {}
    if device:
        context_args.update(pw.devices[device])
    if geolocation:
        context_args["geolocation"] = geolocation
        context_args["permissions"] = ["geolocation"]
    context = browser.new_context(**context_args)
    page = context.new_page()
    return browser, context, page


def login_user(page, email):
    """
    Login to the Expensify app and complete the onboarding.
    """
    # Open the Expensify app
    page.goto(EXPENSIFY_URL)
    # Login user
    page.get_by_test_id("username").fill(email)
    page.get_by_role("button", name="Continue").click()
    otp_code = "123456"
    page.get_by_test_id("validateCode").fill(otp_code)
    try:
        page.get_by_role("button", name="Sign In").click(timeout=2000)
    except:
        pass

def test_room_chat_lhn_preview():
    with sync_playwright() as p:
        browser, context, page = launch_browser(p)
        login_user(page, EMAIL)

        page.get_by_label("My settings").click()
        page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").get_by_text("Workspaces").click()
        page.get_by_label("New workspace").first.click()
        page.get_by_label("Back").click()
        page.get_by_label("Inbox").click()

        admin_channel = page.get_by_test_id('lhn-options-list').get_by_text("#admins").last
        expect(admin_channel).to_be_visible()
        admin_channel.click()

        page.get_by_role('button', name='#admin').click()
        page.get_by_text('Room description').last.click()
        page.locator('div[role="textbox"][aria-label="Room description"]').fill('LHN room preview test')
        page.get_by_role('button', name='Save').click()
        page.mouse.click(0,0)
        page.wait_for_timeout(2000)

        expect(page.get_by_text('removed 0 user')).not_to_be_visible(timeout=1)