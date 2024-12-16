import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright
from utils.trace_cleaner import trace_cleaner


def launch_browser():
    """Launch a persistent browser with the specified platform."""
    playwright = sync_playwright().start()

    browser = playwright.chromium.launch(
        channel="chrome",
        headless=True,
        args=[
            "--ignore-certificate-errors",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
        ],
        proxy={"server": "http://localhost:8080"},
        slow_mo=500,
    )

    context = browser.new_context()
    page = context.new_page()

    return page


def test_unknown_user_profile_load_offline():
    page = launch_browser()
    context = page.context

    # Start tracing
    context.tracing.start(screenshots=True, snapshots=True, sources=True)
    trace_path = "/app/expensify/user_tool/output_browser1.zip"

    try:
        user_email = "t56826807+17350532108421@gmail.com"
        page.goto("https://dev.new.expensify.com:8082/")
        page.locator('input[type="email"]').fill(user_email)
        page.locator("button", has_text="Continue").click()
        otp = "123456"
        page.get_by_role("textbox").fill(otp)

        page.get_by_label("My settings").click()
        page.get_by_role("menuitem", name="Profile").click()
        page.get_by_role("menuitem", name="Address").click()
        page.get_by_label("Address line 1").get_by_role("textbox").fill("Central Park")
        page.locator("#result-list-id > div > div:nth-child(2)").click()
        page.wait_for_timeout(1000)

        address_text = page.get_by_test_id("AddressPage").inner_text()
        assert (
            "e.g." in address_text
        ), "Zip code hint does not begin with 'e.g.' on profile > address"

        page.get_by_label("Back").last.click()
        page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()
        page.get_by_label("row").click()
        page.get_by_label("Workflows").click()
        page.get_by_label("Connect bank account").click()

        personal_info_text = page.locator('div[data-testid="PersonalInfo"]').inner_text()
        assert (
            "e.g." in personal_info_text
        ), "Zip code hint does not begin with 'e.g.' on connect bank account > address"
    except Exception as e:
        # Optionally log or handle the exception here
        raise e
    finally:
        # Ensure the trace is stopped and exported, even if the test fails
        context.tracing.stop()
        context.tracing.export(trace_path)
        # Call the trace cleaner on the saved trace
        trace_cleaner(trace_path)
