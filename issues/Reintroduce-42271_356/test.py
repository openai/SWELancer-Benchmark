import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright._impl._page import Page
from playwright.sync_api import sync_playwright, expect
import re

NEWDOT_URL = "https://dev.new.expensify.com:8082/"
login_email_address = "nitish.expensify+100@gmail.com"


def create_workspace_and_enable_feature(page: Page, feature: str):
    """
    Creates a new workspace and enables a specified feature.

    Args:
        page (Page): The Playwright page object.
        feature (str): The feature to enable (e.g., "Invoices").
    """
    page.locator('button[aria-label="Workspaces"]').click()

    page.get_by_test_id("WorkspaceSwitcherPage").get_by_role(
        "button", name="New workspace"
    ).click()

    page.locator('div[aria-label="More features"]').click()

    # Toggle feature
    toggle_button = page.locator(f'button[aria-label="{feature}"]')
    if not toggle_button.is_checked():
        toggle_button.click()

    page.locator('div[aria-label="Tags"]').click()


def create_tag(page: Page, tag_name: str):
    page.locator("button", has_text="Add tag").click()

    page.locator('input[aria-label="Name"]').fill(tag_name)

    page.locator('button[data-listener="Enter"]', has_text="Save").click()


def select_all_tags(page: Page, check: bool):
    select_all = page.locator('div[aria-label="Select all"][role="checkbox"]')
    if (not select_all.is_checked() and check) or (
        select_all.is_checked() and not check
    ):
        select_all.click()

    if check:
        return page.locator('button[data-listener="Enter"]').inner_text()
    else:
        return None


def delete_tag(page: Page, tag_name: str):
    page.locator(f'button[id="{tag_name}"]').click()

    page.locator('div[aria-label="Delete"]').click()

    page.locator('button[data-listener="Enter"]').click()


def new_dot_login(page, email):
    page.goto(NEWDOT_URL)
    page.locator('input[type="email"]').fill(email)
    page.get_by_role("button", name="Continue").nth(0).click()

    try:
        expect(page.get_by_role("button", name="Sign in")).to_be_visible()
        page.get_by_test_id("validateCode").fill("123456")
    except Exception:
        page.get_by_role("button", name="Join").click()


def test_expensify():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=[
            "--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"],
            slow_mo=1000)

        context_args = {}
        context_args["timezone_id"] = "Asia/Calcutta"

        first_user_context = browser.new_context(
            ignore_https_errors=True, **context_args)
        page = first_user_context.new_page()
        new_dot_login(page, login_email_address)

        create_workspace_and_enable_feature(
            page, "Classify costs and track billable expenses."
        )

        create_tag(page, "tag 1")
        create_tag(page, "tag 2")

        selected_text = select_all_tags(page, check=True)

        total_tags = int(re.search(r"\d+", selected_text).group())
        assert total_tags == 2, "Invalid number of tags selected before deleting a tag!"

        select_all_tags(page, check=False)
        delete_tag(page, "tag 2")
        create_tag(page, "tag 3")

        selected_text = select_all_tags(page, check=True)
        total_tags = int(re.search(r"\d+", selected_text).group())
        assert total_tags == 2, "Invalid number of tags selected after deleting a tag!"

        page.close()
        browser.close()
