import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from playwright._impl._page import Page


def launch_browser(playwright, platform="desktop"):

    mobile_context = {}

    if platform.lower() == "mobile":
        mobile_context = {
            "viewport": {"width": 540, "height": 864},
            "is_mobile": True,
        }

    browser = playwright.chromium.launch(
                channel="chrome",
                headless=True,
                args=[
                    "--ignore-certificate-errors",
                    "--disable-web-security",
                    "--disable-features=IsolateOrigins,site-per-process"
                ],
                proxy={"server": "http://localhost:8080"},
                slow_mo=500
            )
        
    context = browser.new_context(timezone_id = "Asia/Karachi", **mobile_context)
    page = context.new_page()

    return context, page


def login_user(page: Page, first_name="Asaad", last_name="I"):
    page.bring_to_front()

    page.goto("https://dev.new.expensify.com:8082/")

    email = "lbrxifzk+1735219804@gmail.com"

    page.get_by_test_id("username").fill(email)
    page.get_by_role('button', name="Continue").click()
    page.get_by_role('button', name="Join").click()

    try:
        expect(page.locator("text=What do you want to do today?")).to_be_visible()
        page.get_by_text("Track and budget expenses").click()
        page.get_by_role("button", name="Continue").click()
        page.get_by_role("textbox", name="First name").fill(first_name)
        page.get_by_role("textbox", name="Last name").fill(last_name)
        page.get_by_role("button", name="Continue").click()
    except:
        pass


def handle_close_btn(page):
    try:
        close_btn = page.get_by_label("Close")
        expect(close_btn).to_be_visible()
        close_btn.click()
    except:
        pass


def test_qbo_connection_alignment_in_accounting_settings_narrow_layout():
    from utils.trace_cleaner import trace_cleaner
    playwright = sync_playwright().start()
    context, page = launch_browser(playwright, "mobile")

    try:
        context.tracing.start(screenshots=True, snapshots=True, sources=True)

        login_user(page, "Asaad", "I")
        handle_close_btn(page)

        page.get_by_label("Start chat (Floating action)").click()
        page.get_by_label("New workspace").click()
        page.get_by_label("More features").click()
        page.get_by_label("Sync your chart of accounts").click()
        page.get_by_label("Accounting").click()


        qbo_text_box = page.get_by_text("Quickbooks Online", exact=True).bounding_box()
        qbo_text_box_center_y = qbo_text_box["y"] + qbo_text_box["height"] / 2
        connect_button_box = (
            page.get_by_label("Quickbooks Online")
            .get_by_role("button", name="Connect")
            .bounding_box()
        )
        connect_button_center_y = connect_button_box["y"] + connect_button_box["height"] / 2


        tolerance = 1
        assert (
            abs(qbo_text_box_center_y - connect_button_center_y) < tolerance
        ), "Text and button are not vertically center-aligned."

    except Exception as e:
        raise e
    finally:
        context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
        trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
        context.close()
        playwright.stop()
