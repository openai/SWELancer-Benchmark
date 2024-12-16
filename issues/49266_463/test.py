import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import pytest
from playwright.sync_api import sync_playwright, Page

SITE_URL = "https://dev.new.expensify.com:8082/"
PRIMARY_EMAIL = "expensifyolddot+1733631442@gmail.com"
FIRST_NAME = "Expenolddot"
LAST_NAME = "1733631442"


@pytest.fixture
def setup_playwright():
    playwright = sync_playwright().start()

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
    context_args = {}
    context_args["timezone_id"] = "Asia/Kathmandu"
    context = browser.new_context(**context_args)

    yield context

    # Cleanup: close browsers and stop Playwright
    browser.close()
    playwright.stop()


def login_user(page: Page, email: str):
    page.goto(SITE_URL)
    page.locator('input[type="email"]').fill(email)
    page.locator('button[tabindex="0"]').click()
    try:
        page.locator("button", has_text="Join").click()
    except Exception:
        pass


def complete_onboarding(page: Page, fname: str, lname: str):
    page.locator("text='Track and budget expenses'").click()
    page.locator('input[name="fname"]').fill(fname)
    page.locator('input[name="lname"]').fill(lname)
    page.get_by_role("button", name="Continue").last.click()


def is_connected(page: Page):
    text = page.locator('div[aria-label="NetSuite"][role="menuitem"]').last.inner_text()
    return "Last synced" in text


@pytest.mark.parametrize(
    "setup_playwright",
    [{"width": 1280, "height": 360}],
    indirect=True,
)
def test(setup_playwright):
    context = setup_playwright

    page = context.new_page()

    login_user(page, PRIMARY_EMAIL)

    complete_onboarding(page, FIRST_NAME, LAST_NAME)

    page.locator('button[aria-label="Workspaces"]').click()
    page.get_by_test_id("WorkspaceSwitcherPage").get_by_role(
        "button", name="New workspace"
    ).click()

    page.locator('div[aria-label="More features"]').click()
    page.locator('button[aria-label="Sync your chart of accounts and more."]').click()
    page.locator('div[aria-label="Accounting"]').click()
    (
        page.locator('div[aria-label="NetSuite"]')
        .locator("button", has_text="Connect")
        .click()
    )

    page.locator("button", has_text="Upgrade").last.click()
    page.locator("button", has_text="Got it, thanks").last.click()
    page.locator("button", has_text="Next").last.click()
    page.locator("button", has_text="Next").last.click()
    page.locator("button", has_text="Next").last.click()
    page.locator("button", has_text="Next").last.click()

    page.locator('input[aria-label="NetSuite Account ID"]').last.fill("123")
    page.locator('input[aria-label="Token ID"]').last.fill("123")
    page.locator('input[aria-label="Token Secret"]').last.fill("123")
    page.locator("button", has_text="Confirm").last.click()

    # Wait for connection to complete
    page.wait_for_timeout(5000)
    page.reload()

    new_page = context.new_page()
    new_page.goto(
        f"https://dev.new.expensify.com:8082/settings/workspaces/{page.url.split('/')[-2]}/accounting/netsuite/import/custom-segment/new"
    )

    new_page.locator('button[aria-label="Custom segment"]').last.click()
    new_page.locator("button", has_text="Next").last.click()
    new_page.locator('input[aria-label="Name"]').last.fill("abc")
    new_page.locator("button", has_text="Next").last.click()
    new_page.locator("button", has_text="Next").last.click()
    new_page.locator('button[aria-label="Back"]').last.click()

    rhn_text = new_page.locator(
        'div[data-testid="NetSuiteImportAddCustomSegmentPage"]'
    ).last.inner_text()

    assert (
        "Please fix the errors in the form before continuing." not in rhn_text
    ), "Error message did not disappear!"