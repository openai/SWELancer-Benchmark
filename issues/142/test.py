import pytest_asyncio
import pytest

from playwright.async_api import async_playwright, expect, Page
from utils.login import EmailHandler, complete_onboarding

NEWDOT_URL = "http://dev.new.expensify.com:8082/"
EXPENSIFY_EMAIL = "testingq186+52137@gmail.com"
EXPENSIFY_PASSWORD = "kkfr hqiv yuxq rbso"
FIRST_NAME = "Testing"
LAST_NAME = "52137"

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

async def create_workspace_and_create_tag(page: Page):
    await page.get_by_label("My settings").click()
    await page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()
    await page.get_by_label("New workspace").click()
    await expect(page.get_by_test_id("WorkspaceInitialPage").get_by_text(f"{FIRST_NAME} {LAST_NAME}'s Workspace")).to_be_visible()
    await page.get_by_label("More features").click()
    await page.get_by_label("Classify costs and track").click()
    await page.get_by_label("Tags").click()
    await page.get_by_role("button", name="Add tag").click()
    await page.get_by_role("textbox", name="Name").click()
    await page.get_by_role("textbox", name="Name").fill("California")
    await page.get_by_role("button", name="Save").click()
    await page.get_by_test_id("WorkspaceTagsPage").get_by_role("button", name="Settings").click()
    await page.get_by_label("Tag", exact=True).click()
    await page.get_by_role("textbox", name="Custom tag name").click()
    await page.get_by_role("textbox", name="Custom tag name").fill("State")
    await page.get_by_role("button", name="Save").click()
    await page.get_by_label("Members must tag all expenses").click()
    await page.get_by_test_id("WorkspaceTagsSettingsPage").get_by_label("Back").click()
    await page.get_by_label("Back").click()
    await page.get_by_label("Inbox").click()

@pytest.mark.asyncio(loop_scope="function")
async def test_tag_auto_selected_in_case_of_only_one_tag(page: Page):
    await new_dot_login(page, EXPENSIFY_EMAIL, EXPENSIFY_PASSWORD)

    try:
        # Check if a workspace exists
        await expect(page.get_by_label("Navigates to a chat").get_by_text(f"{FIRST_NAME} {LAST_NAME}'s Workspace").first).to_be_visible()
    except Exception:
        # Create a workspace if does not exist
        await create_workspace_and_create_tag(page)

    await page.get_by_label("Navigates to a chat").get_by_text(f"{FIRST_NAME} {LAST_NAME}'s Workspace").first.click(timeout=10_000)
    
    await page.get_by_label("Create").last.click()
    try:
        await page.get_by_label("Create expense").click(timeout=5000)
    except Exception:
        await page.get_by_label("Submit expense").click(timeout=5000)
    await page.get_by_label("Manual").click()
    await page.get_by_placeholder("0").click()
    await page.get_by_placeholder("0").fill("1")
    await page.locator("#numPadContainerView").get_by_role("button", name="Next").click()
    # The text 'required' should not be visible
    await expect(page.get_by_role("menuitem", name="State").get_by_text("Required")).not_to_be_visible()
    # 'California' should be visible
    await expect(page.get_by_label("California")).to_be_visible()
