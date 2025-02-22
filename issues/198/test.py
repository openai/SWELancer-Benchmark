import re
import pytest
import random
from playwright.async_api import async_playwright, expect, Page, Browser, TimeoutError
from playwright.async_api._context_manager import PlaywrightContextManager


NEWDOT_URL = "https://dev.new.expensify.com:8082"

USERNAME = "doorsqueaky"
DOMAIN = "gmail.com"

ADMIN_FNAME = "John"
ADMIN_LNAME = "Doe"
USER_FNAME = "John"
USER_LNAME = "Smith"

MAX_TRIES = 5


def generate_random_email(username: str=USERNAME, 
                          domain: str=DOMAIN) -> str:
    """
        Generates a random email address given a username and domain
    """
    return f"{username}+{random.randint(1000000, 9999999999)}@{domain}"


async def launch_browser(p: PlaywrightContextManager) -> tuple[Browser, Page]:
    """
        Launches a new browser and a new page
    """
    browser = await p.chromium.launch(
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
    page = await browser.new_page()

    return browser, page


async def login_user(page: Page, email: str, 
                     first_name: str, last_name: str) -> None:
    """
        Logs in a user to Expensifyn NEW Dot
    """
    # Step 1: Open the Expensify NEW Dot URL
    await page.goto(NEWDOT_URL)

    # Step 2: Enter the email and click continue
    await page.get_by_test_id("username").fill(email)
    await page.get_by_role("button", name="Continue").click()

    # Step 3: Click on the Join
    await page.get_by_role("button", name="Join").click()
    
    # step 4: Complete the onboarding process
    await page.locator("text='Track and budget expenses'").click()

    await page.locator('input[name="fname"]').fill(first_name)
    await page.locator('input[name="lname"]').fill(last_name)
    await page.get_by_role("form").get_by_role("button", name="Continue").click()


async def create_workspace(page: Page, user_email: str, user_name: str) -> None:
    """
        Creates a new workspace, adds a user, 
        enables workflow and adds approvals
    """

    # Click on workspaces under settings
    await page.locator('button[aria-label="My settings"]').click()
    await page.locator('div[aria-label="Workspaces"][role="menuitem"]').click()

    # click on New Workspace to create a new workspace
    await page.locator('button[aria-label="New workspace"]').first.click()

    # Click on members and add user
    await page.locator('div[aria-label="Members"][role="menuitem"]').click()
    await page.get_by_role('button', name="Invite member").click()

    await page.locator('input[aria-label="Name, email, or phone number"]').fill(user_email)
    await page.locator(f'button[aria-label="{user_name}"]', has_text=user_email).click()

    await page.get_by_role('button', name="Next").click()
    await page.get_by_role('button', name="Invite").last.click()

    # Enable workflow under more features and add approvals
    await page.locator('div[aria-label="More features"][role="menuitem"]').click()
    workflow_toggle = page.locator('button[aria-label="Configure how spend is approved and paid."]')
    workflow_toggle_checked =  await workflow_toggle.get_attribute("aria-checked") == "true"

    if not workflow_toggle_checked:
        await workflow_toggle.click()

    await page.locator('div[aria-label="Workflows"][role="menuitem"]').click()
    add_approval_toggle = page.locator('button[aria-label="Require additional approval before authorizing a payment."]')
    add_approval_toggle_checked = await add_approval_toggle.get_attribute("aria-checked") == "true"

    if not add_approval_toggle_checked:
        await add_approval_toggle.click()

    # Go back to Inbox
    await page.locator('button[aria-label="Back"]').click()
    await page.locator('button[aria-label="Inbox"]').click()


async def submit_expense(page: Page, amount: int, admin_name: str) -> None:
    """
        Submits an expense to the workspace
    """
    # Click on the floating action button
    await page.locator('button[aria-label="Start chat (Floating action)"]').click()

    # Click on Submit expense
    await page.locator('div[aria-label="Submit expense"][role="menuitem"]').click()

    # Click on Manual
    await page.locator('button[aria-label="Manual"]').click()

    # Select the current USD - $
    await page.locator('button[aria-label="Select a currency"]').click()
    await page.locator('div[data-testid="IOURequestStepCurrency"]').\
        locator('input').fill("USD")
    await page.locator('button[aria-label="USD - $"]').click()

    # Enter the amount
    await page.locator('div[data-testid="IOURequestStartPage"]').\
        locator('input[placeholder="0"]').fill(str(amount))

    # Click on Next
    await page.get_by_role('button', name="Next").first.click()

    # Select the workspace to submit the expense
    await page.locator('div[data-testid="IOURequestStepParticipants"]').\
        locator('input[aria-label="Name, email, or phone number"]').fill(admin_name)
    await page.locator(f'button[aria-label="{admin_name}\'s Workspace"]').click()

    # Enter merchant details
    await page.locator('div[role="menuitem"]', has_text="Merchant").click()  
    await page.locator('input[aria-label="Merchant"]').fill("Amazon")
    await page.get_by_role('button', name="Save").click()

    # Click on Submit expense
    await page.get_by_role('button', name=f"Submit ${amount}.00").click()


async def hold_expense(page: Page, user_name: str, admin_name: str) -> None:

    # Reload the page
    await page.reload()

    # Click on the workspace chat 
    await page.locator('button[aria-label="Navigates to a chat"]',
                       has_text=re.compile(f"{admin_name}'s Workspace owes .+")).click()
    
    # Open the expense report
    await page.locator('button[aria-label="View details"]',
                       has_text=re.compile(f"{admin_name}'s Workspace owes:")).click()
    
    report_id = page.url.split("/")[-1]
    # Hold the expense
    await page.locator(f'button[aria-label="Expense Report #{report_id}"]').first.click()
    await page.get_by_role('button', name="Hold").click()

    await page.locator('input[aria-label="Reason"]').fill("Provide further details")
    await page.get_by_role('button', name="Hold expense").click()

    try:
        await page.get_by_role('button', name="Got it").click(timeout=5000)
    except TimeoutError:
        pass


async def open_expense_report(page: Page, admin_name: str) -> None:
    """
        Opens the expense report for the user
    """
    # Click on the workspace chat 
    await page.locator('button[aria-label="Navigates to a chat"]',
                       has_text=re.compile(f"{admin_name}'s Workspace owes .+")).click()
    
    # Open the expense report
    await page.locator('button[aria-label="View details"]',
                       has_text=re.compile(f"{admin_name}'s Workspace owes:")).first.click()
    
    try:
        await page.get_by_role('button', name="Got it").click(timeout=5000)
    except TimeoutError:
        pass


async def check_rbr(page: Page, user_name: str, admin_name: str):
    """
        Checks if the inbox has an RBR
    """
    # Open the expense report
    await open_expense_report(page, admin_name)

    # Click on non-RBR chat. Clear cache and restart
    await page.locator('button[aria-label="Navigates to a chat"]',
                       has_text=f"{user_name} (you)").click()
    
    await page.locator('button[aria-label="My settings"]').click()
    await page.locator('div[aria-label="Troubleshoot"][role="menuitem"]').click()

    await page.locator('div[aria-label="Clear cache and restart"][role="menuitem"]').click()
    await page.get_by_role('button', name="Reset and refresh").click()

    await page.wait_for_timeout(3000)

    # Check RBR on Inbox
    inbox_bottom_button = page.locator('button[aria-label="Inbox"]')
    await inbox_bottom_button.click()

    await open_expense_report(page, admin_name)
    # Expect div elemented with Red dot (RBR) to be visible
    await expect(inbox_bottom_button.locator('div[style*="background-color: rgb(242, 87, 48)"]')).to_be_visible()


@pytest.mark.asyncio
async def test_inbox_rbr():
    """
        Tests that inbox has correct rbr 
        when there's a chat with rbr
    """
    async with async_playwright() as p:
        browser_admin, page_admin = await launch_browser(p)
        browser_user, page_user = await launch_browser(p)

        # Login user and admin to respective workspaces
        # admin_email = generate_random_email()
        # user_email = generate_random_email()

        # Hard coded emails for flow replay
        user_email = "doorsqueaky+2851020272@gmail.com"
        admin_email = "doorsqueaky+7589891911@gmail.com"

        await login_user(page_admin, admin_email, ADMIN_FNAME, ADMIN_LNAME)
        await login_user(page_user, user_email, USER_FNAME, USER_LNAME)

        admin_name = f"{ADMIN_FNAME} {ADMIN_LNAME}"
        user_name = f"{USER_FNAME} {USER_LNAME}"

        # Admin creates a new workspace, enalbes workflow and adds user
        await create_workspace(page_admin, user_email, user_name)

        # User submits an expense to the workspace
        await submit_expense(page_user, 6, admin_name)

        # Admin puts the expense on hold
        await hold_expense(page_admin, user_name, admin_name)

        # Check Inbox is RBRed
        await check_rbr(page_user, user_name, admin_name)

