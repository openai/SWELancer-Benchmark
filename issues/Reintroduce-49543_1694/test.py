import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright
from playwright.sync_api._context_manager import PlaywrightContextManager

USER_EMAIL = "expensify66+92365465438764676543435435@gmail.com"
URL = "https://dev.new.expensify.com:8082"
PASS_CODE = "142377"


def login_user(page):
    page.goto(URL)
    page.get_by_test_id("username").fill(USER_EMAIL)
    page.get_by_role("button", name="Continue").click()
    validate_code_input = page.locator('input[data-testid="validateCode"]')
    validate_code_input.fill(PASS_CODE)


def get_context(p: PlaywrightContextManager, browser, is_phone_setup=False):
    # Define browser context options
    context_options = {
        "permissions": ["clipboard-read", "clipboard-write"],
        "reduced_motion": "no-preference",
    }

    if is_phone_setup:
        context_options.update(p.devices["iPhone 12 Pro"])

    # Create a normal browser context
    context = browser.new_context(**context_options)

    # Open a new page
    page = context.new_page()

    return context, page


def enable_rules(page):
    page.get_by_label("My settings").click()
    page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").get_by_text(
        "Workspaces"
    ).click()
    page.get_by_role("button", name="row").first.click()
    page.get_by_text("More features").click()
    page.get_by_label("Configure when receipts are").click()
    page.get_by_label("Classify costs and track").click()


def assert_tag_rules_not_visible(page):
    page.get_by_test_id("WorkspaceInitialPage").get_by_text("Tags").click()
    page.get_by_label("State").click()
    page.locator("#CA").click()
    assert not page.get_by_text("Tag rules").is_visible()


def test_login():
    with sync_playwright() as p:
        # Launch the browser with the specified arguments
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--ignore-certificate-errors",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
            ],
        )

        # This test assumes that the user has already setup in the old dot
        # And uploaded custom tags through spreadsheet
        context, page = get_context(p, browser)
        login_user(page)
        enable_rules(page)
        assert_tag_rules_not_visible(page)
        page.close()
        context.close()
        browser.close()