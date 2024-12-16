import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import pytest
from playwright.sync_api import sync_playwright, Page
from utils.trace_cleaner import trace_cleaner

static_email = "randomturing+40121577@gmail.com"

@pytest.fixture
def setup_playwright(request):
    width = getattr(request, "param", {}).get("width", 1280)
    height = getattr(request, "param", {}).get("height", 720)

    playwright = sync_playwright().start()

    browser = playwright.chromium.launch(
        headless=True, slow_mo=1000, args=["--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"]
    )

    context = browser.new_context(viewport={"width": width, "height": height})
    page = context.new_page()

    yield page

    # Cleanup
    browser.close()
    playwright.stop()


def login_user(page: Page, email: str, first_name: str, last_name: str):
    page.goto("https://dev.new.expensify.com:8082/")
    page.locator('input[type="email"]').fill(email)
    page.locator('button[tabindex="0"]').click()
    page.locator("button", has_text="Join").click()

    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()


def create_workspace(page: Page):
    page.locator('button[aria-label="Workspaces"]').click()

    page.get_by_test_id("WorkspaceSwitcherPage").get_by_role(
        "button", name="New workspace"
    ).click()

    page.locator('button[aria-label="Back"]').nth(0).click()

    page.locator('button[aria-label="Back"]').nth(0).click()


def browse_to_workspace(page: Page, workspace_name: str):
    page.locator('button[aria-label="Workspaces"]').click()
    try:
        page.locator(f'button[aria-label="{workspace_name}"]').click()
    except Exception:
        page.locator(f'button[aria-label="{workspace_name}"]').nth(1).click()
    page.locator(
        'button[aria-label="Navigates to a chat"]', has_text=workspace_name
    ).nth(0).click()

@pytest.mark.parametrize(
    "setup_playwright",
    [{"width": 1280, "height": 720}],
    indirect=True,
)
def test(setup_playwright):
    page = setup_playwright
    trace_path = "/app/expensify/user_tool/output_browser1.zip"

    # Start tracing
    context = page.context
    context.tracing.start(screenshots=True, snapshots=True)

    try:
        first_name, last_name = "Alex", "Smith"
        email = static_email
        login_user(page, email, first_name, last_name)

        create_workspace(page)
        workspace_name = f"{first_name} {last_name}'s Workspace"

        # Create
        page.locator(
            'button[aria-label="Start chat (Floating action)"][tabindex="0"]'
        ).click()

        page.locator('div[aria-label="Submit expense"]').click()
        page.locator('button[aria-label="Distance"]').click()

        page.locator('div[data-tag="pressable"]', has_text="Start").click()
        page.locator('div[aria-label="Address"]').locator("input").fill("Central Park")
        page.locator('div[id="result-list-id"]').locator(
            "div", has_text="Central Park"
        ).first.click()

        page.locator('div[data-tag="pressable"]', has_text="Stop").click()
        page.locator('div[aria-label="Address"]').locator("input").fill("Brooklyn")
        page.locator('div[id="result-list-id"]').locator(
            "div", has_text="Brooklyn"
        ).first.click()

        page.locator('button[data-listener="Enter"]', has_text="Next").last.click()

        page.locator('input[aria-label="Name, email, or phone number"]').fill(
            workspace_name
        )
        page.locator(f'button[aria-label="{workspace_name}"]').last.click()
        page.locator('button[data-listener="Enter"]').last.click()

        page.locator('button[aria-label="View details"]').click()
        page.locator('div[data-testid="report-actions-list"]').locator(
            'div[data-tag="pressable"]', has_text="Distance"
        ).click()

        page.locator("button", has_text="Add stop").click()
        page.locator('div[aria-label="Address"]').locator("input").fill("Times Square")
        page.locator('div[id="result-list-id"]').locator(
            "div", has_text="Times Square"
        ).first.click()

        page.locator('button[data-listener="Enter"]', has_text="Save").last.click()

        distance = (
            page.locator('div[data-testid="report-actions-list"]')
            .locator('div[data-tag="pressable"]', has_text="Distance")
            .inner_text()
        )

        print(distance)
        assert "Pending" not in distance, "Distance is not optimistically updating!"

    finally:
        # Stop tracing and clean trace
        context.tracing.stop(path=trace_path)
        trace_cleaner(trace_path)
