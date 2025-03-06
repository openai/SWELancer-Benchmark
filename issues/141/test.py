import pytest_asyncio
import pytest

from playwright.async_api import async_playwright, expect, Page
from utils.login import EmailHandler, complete_onboarding

NEWDOT_URL = "http://dev.new.expensify.com:8082/"
EXPENSIFY_EMAIL = "testingq186+52140@gmail.com"
EXPENSIFY_PASSWORD = "kkfr hqiv yuxq rbso"
FIRST_NAME = "Testing"
LAST_NAME = "52140"

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
    context.set_default_timeout(30_000)
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

async def create_workspace_and_add_company_card(page: Page):
    await page.get_by_label("My settings").click()
    await page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()
    try:
        # Check if the workspace already exists
        await expect(page.get_by_label("row").get_by_text(f"{FIRST_NAME} {LAST_NAME}'s Workspace", exact=True)).to_be_visible(timeout=5000)
        await page.get_by_label("row").get_by_text(f"{FIRST_NAME} {LAST_NAME}'s Workspace", exact=True).click()
        await page.get_by_test_id("WorkspaceInitialPage").get_by_label("Company cards").click()
    except Exception:
        # Create a new workspace and add a card
        await page.get_by_label("New workspace").click()
        await expect(page.get_by_test_id("WorkspaceInitialPage").get_by_text(f"{FIRST_NAME} {LAST_NAME}'s Workspace", exact=True)).to_be_visible()
        await page.get_by_label("More features").click()
        await page.get_by_label("Import spend from existing").click()
        await page.get_by_role("button", name="Upgrade").click()
        await page.get_by_role("button", name="Got it, thanks").click()
        await page.get_by_test_id("WorkspaceInitialPage").get_by_label("Company cards").click()
        await page.get_by_label("Add company cards").click()
        await page.get_by_label("American Express").click()
        await page.get_by_role("button", name="Next").click()
        await page.get_by_label("American Express Corporate").click()
        await page.get_by_role("button", name="Next").click()
        await page.get_by_role("button", name="Next").click()
        await page.get_by_role("textbox").click()
        await page.get_by_role("textbox").fill("Delivery file name")
        await page.get_by_role("button", name="Submit").click()
    finally:
        await expect(page.get_by_label("American Express cards")).to_be_visible(timeout=10_000)

@pytest.mark.asyncio
async def test_correct_card_name_displayed_after_refresh(page: Page):
    await new_dot_login(page, EXPENSIFY_EMAIL, EXPENSIFY_PASSWORD)
    await create_workspace_and_add_company_card(page)
    await page.get_by_role("button", name="Settings", exact=True).click()
    await page.get_by_text("Card feed name").click()
    # Correct name before reload
    await expect(page.get_by_role("textbox", name="Name")).to_have_value("American Express cards")
    await page.reload()

    # Should not show 'undefined'
    await expect(page.get_by_role("textbox", name="Name")).not_to_have_value("undefined cards")
    # Should show the correct name
    await expect(page.get_by_role("textbox", name="Name")).to_have_value("American Express cards")
