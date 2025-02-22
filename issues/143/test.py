import pytest_asyncio
import pytest

from playwright.async_api import async_playwright, expect, Page
from utils.login import EmailHandler, complete_onboarding

NEWDOT_URL = "http://dev.new.expensify.com:8082/"
EXPENSIFY_EMAIL = "testingq186+52131@gmail.com"
EXPENSIFY_PASSWORD = "kkfr hqiv yuxq rbso"
FIRST_NAME = "Testing"
LAST_NAME = "52131"

TESTING_FLOW = True

@pytest_asyncio.fixture
async def page():
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
    page = await context.new_page()

    yield page
    await browser.close()
    await pw.stop()

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
            await expect(page.get_by_label("My settings")).to_be_visible(timeout=10_000)
            # Force onboarding modal to pop up
            await page.goto("https://dev.new.expensify.com:8082/onboarding/purpose")
            await complete_onboarding(page, FIRST_NAME, LAST_NAME)

async def create_workspace_and_disable_categories(page: Page):
    await page.get_by_label("My settings").click()
    await page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()
    await page.get_by_label("New workspace").click()
    await page.get_by_label("Categories").click()
    await page.get_by_label("Select all").click()
    await page.get_by_role("button", name="selected").click()
    await page.get_by_label("Disable categories").click()
    await page.get_by_label("Back").click()
    await page.get_by_label("Inbox").click()

async def submit_expense_and_categorize(page: Page):
    await page.get_by_label("Navigates to a chat").get_by_text(f"{FIRST_NAME} {LAST_NAME} (you)").click(timeout=10_000)
    await page.get_by_label("Create").last.click()
    try:
        # Check if 'Track expense' is shown instead of 'Create expense'
        await page.get_by_label("Track expense").click()
    except Exception:
        await page.get_by_label("Create expense").click()
    await page.get_by_label("Manual").click()
    await page.get_by_placeholder("0").click()
    await page.get_by_placeholder("0").fill("12")
    await page.locator("#numPadContainerView").get_by_role("button", name="Next").click()
    await page.get_by_role("button", name="Track expense").click()
    await page.get_by_role("button", name="Categorize it").click()
    await page.get_by_role("button", name="Edit categories").click()

@pytest.mark.asyncio
async def test_categories_checkbox_visibility_in_RHP(page: Page):
    await new_dot_login(page, EXPENSIFY_EMAIL, EXPENSIFY_PASSWORD)
    await page.get_by_label("Navigates to a chat").get_by_text(f"{FIRST_NAME} {LAST_NAME} (you)").click(timeout=10_000)
    try:
        await expect(page.get_by_role("button", name="Categorize it")).to_be_visible()
        await page.get_by_role("button", name="Categorize it").click()
        await page.get_by_role("button", name="Edit categories").click()
    except Exception:
        await create_workspace_and_disable_categories(page)
        await submit_expense_and_categorize(page)
    
    await expect(page.get_by_label("Select all")).to_be_visible()
