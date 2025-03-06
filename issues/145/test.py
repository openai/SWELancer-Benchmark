import pytest_asyncio
import pytest

from playwright.async_api import async_playwright, expect, Page, BrowserContext
from utils.login import EmailHandler, complete_onboarding

NEWDOT_URL = "http://dev.new.expensify.com:8082/"
EXPENSIFY_EMAIL = "testingq186+52123_1@gmail.com"
EXPENSIFY_PASSWORD = "kkfr hqiv yuxq rbso"
FIRST_NAME = "Testing"
LAST_NAME = "52123"

TESTING_FLOW = True

@pytest_asyncio.fixture
async def context():
    """
    Launch the Expensify app.
    """
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(
        channel="chrome",
        headless=False,
        args=[
            "--ignore-certificate-errors",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ],
        proxy={"server": "http://localhost:8080"},
        slow_mo=500
    )
    context = await browser.new_context(ignore_https_errors=True)

    yield context

    await context.close()
    await browser.close()
    await pw.stop()

@pytest_asyncio.fixture
async def page(context: BrowserContext):
    page = await context.new_page()

    yield page

async def new_dot_login(page: Page, email, password):
    await page.goto(NEWDOT_URL)
    with EmailHandler(email, password) as email_handler:
        if not TESTING_FLOW :
            email_handler.clean_inbox()  # Clean inbox

        # Enter email
        await page.get_by_role("textbox", name="Phone or email").fill(email)
        await page.get_by_role("button", name="Continue").click()

        try:
            await expect(page.locator('input[name="validateCode"]').first).to_be_visible()
            otp = email_handler.read_otp_code() if not TESTING_FLOW else "123456"
            await page.locator('input[name="validateCode"]').first.fill(str(otp))
            # Wait sign in to complete
            await page.get_by_text("Please enter the magic code").wait_for(state="hidden")
        except Exception:
            await page.get_by_role("button", name="Join").click()
            await complete_onboarding(page, FIRST_NAME, LAST_NAME)

@pytest.mark.asyncio
async def test_distance_receipt_placeholder_opacity(context: BrowserContext, page: Page):
    await new_dot_login(page, EXPENSIFY_EMAIL, EXPENSIFY_PASSWORD)

    try:
        # Check if a workspace exists
        await expect(page.get_by_label("Navigates to a chat").get_by_text(f"{FIRST_NAME} {LAST_NAME}'s Workspace").first).to_be_visible()
    except Exception:
        # Create a workspace if does not exist
        await page.get_by_label("My settings").click()
        await page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()
        await page.get_by_label("New workspace").click()
        await expect(page.get_by_test_id("WorkspaceInitialPage").get_by_text(f"{FIRST_NAME} {LAST_NAME}'s Workspace")).to_be_visible()
        await page.get_by_label("Back").click()
        await page.get_by_label("Inbox").click()

    await page.get_by_label("Navigates to a chat").get_by_text(f"{FIRST_NAME} {LAST_NAME}'s Workspace").first.click(timeout=10_000)
    await context.set_offline(True)
    await page.get_by_label("Create").last.click()
    await page.get_by_label("Submit expense").click()
    try:
        # React error boundary overlay
        await page.locator("#react-refresh-overlay").content_frame.get_by_role("button", name="× Close").click(timeout=8_000)
    except Exception:
        pass
    await page.get_by_label("Distance").click()
    await page.get_by_test_id("IOURequestStartPage").get_by_role("button", name="Start").click()
    await page.get_by_test_id("IOURequestStepWaypoint").get_by_role("textbox").click()
    await page.get_by_test_id("IOURequestStepWaypoint").get_by_role("textbox").fill("abc")
    await page.get_by_role("button", name="Save").click()
    await page.get_by_role("button", name="Stop").click()
    await page.get_by_test_id("IOURequestStepWaypoint").get_by_role("textbox").click()
    await page.get_by_test_id("IOURequestStepWaypoint").get_by_role("textbox").fill("def")
    await page.get_by_role("button", name="Save").click()
    await page.get_by_role("button", name="Next").nth(1).click()
    await page.get_by_role("button", name="Submit expense").click()
    try:
        # React error boundary overlay
        await page.locator("#react-refresh-overlay").content_frame.get_by_role("button", name="× Close").click(timeout=8_000)
    except Exception:
        pass
    await page.get_by_text("Pending...").last.click()
    # Target the svg placeholder
    svg = page.get_by_test_id(f"report-screen-{page.url.split("/")[-1]}").get_by_test_id("report-actions-list").get_by_role("img").first
    # Use the svg placeholde to target its deeply nested parent div whose opacity needs to be tested
    target_div = svg.locator("../../../../../..")

    opacity = await target_div.evaluate("el => getComputedStyle(el).opacity")

    assert opacity == '1', "The placeholder SVG has low opacity, the issue exists"
