import logging
from playwright.async_api import Page, expect
from utils.email_handler import EmailHandler

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# URLs
# Note: Update the URLs to the correct ones as needed
NEW_DOT_URL = "https://dev.new.expensify.com:8082"
OLD_DOT_URL = "http://localhost:9000/"


async def check_if_logged_in(page: Page, url: str):
    """
    Check if the user is already logged in by navigating to the specified URL.
    Args:
        page (Page): The Playwright page object.
        url (str): The URL to navigate to before checking login status.
    Returns:
        bool: True if logged in, False otherwise.
    """
    await page.goto(url)
    try:
        await expect(page.get_by_label("Inbox")).to_be_visible()
        logging.info("User is already logged in.")
        return True
    except:
        logging.info("User is not logged in.")
        return False


# Sign In to Expensify
async def sign_in_new_dot(page: Page, email: str, password: str, mock_otp: bool=False):
    """
    Sign in into the new Expensify dot.
    """
    
    # Sign In
    with EmailHandler(email, password) as email_handler:
        # Clean inbox
        if not mock_otp:
            email_handler.clean_inbox()

        # Enter email
        await page.get_by_test_id("username").fill(email)
        await page.get_by_role("button", name="Continue").click()
  
        # Await OTP
        otp = "123456" if mock_otp else email_handler.read_otp_code()
        await page.get_by_test_id("validateCode").fill(otp)

        # Wait sign in to complete
        await page.get_by_text("Please enter the magic code").wait_for(state="hidden")
        logging.info("Sign in complete.")


async def sign_up_new_dot(page: Page, email: str):
    """
    Sign up into the new Expensify dot.
    """

    # Enter email
    await page.get_by_test_id("username").fill(email)
    await page.get_by_role("button", name="Continue").click()
    await page.get_by_role("button", name="Join").click()
 
    # Wait sign up to complete
    await page.get_by_role("button", name="Join").wait_for(state="hidden")
    logging.info("Sign up complete.")
 
async def sign_in_old_dot(page: Page, email: str, password: str, mock_otp: bool=False):
    """
    Signs in into the old Expensify dot.
    Note this will redirect to the PRODUCTION URL, be careful
    """

    # Sign In
    with EmailHandler(email, password) as email_handler:
        # Clean inbox
        if not mock_otp:
            email_handler.clean_inbox()

        # Enter email
        await page.get_by_role("button", name="Sign In").click()
        await page.get_by_role("button", name="Email ").click()
        await page.get_by_placeholder("Enter your email to begin").fill(email)
        await page.get_by_role("button", name="Next").click()

        # Await OTP
        otp = "123456" if mock_otp else email_handler.read_otp_code()
        await page.get_by_placeholder("Magic Code").fill(otp)
        await page.locator("#js_click_signIn").click()
  
        # Wait sign in to complete
        await page.wait_for_selector('input[placeholder="Magic Code"]', state="hidden")
        logging.info("Sign in complete.")
        
async def sign_up_old_dot(page: Page, email: str):
    """
    Signs up into the old Expensify dot.
    Note this will redirect to the PRODUCTION URL, be careful
    """

    # Select "I want to:" option (Update this as needed)
    await page.locator("#qualifier-individual").check()

    # Enter email
    await page.locator("#login-main").fill(email)
    await page.locator("#js_click_signUp_main").click()
    await page.get_by_role("button", name="Join").click()
    
    # Wait sign up to complete
    await page.locator("#sign-in-modal").get_by_role("img", name="Expensify").wait_for(state="hidden")
    logging.info("Sign up complete.")

# Sign in to Expensify
async def sign_in(page: Page, email: str, password: str, expensify_dot: str="NewDot", url_new_dot: str=None, url_old_dot: str=None, mock_otp: bool=False):
    """
    Sign in into the Expensify dot.
    """

    url_new_dot = url_new_dot if url_new_dot else NEW_DOT_URL
    url_old_dot = url_old_dot if url_old_dot else OLD_DOT_URL

    if expensify_dot == "NewDot":
        if await check_if_logged_in(page=page, url=url_new_dot):
            return
        await sign_in_new_dot(page=page, email=email, password=password, mock_otp=mock_otp)
    elif expensify_dot == "OldDot":
        if await check_if_logged_in(page=page, url=url_old_dot):
            return
        await sign_in_old_dot(page=page, email=email, password=password, mock_otp=mock_otp)
    else:
        raise ValueError("Invalid Expensify dot provided. Please provide either 'NewDot' or 'OldDot'.")

# Sign up to Expensify
async def sign_up(page: Page, email: str, expensify_dot: str="NewDot", url_new_dot: str=None, url_old_dot: str=None):
    """
    Sign up into the Expensify dot.
    """
    url_new_dot = url_new_dot if url_new_dot else NEW_DOT_URL
    url_old_dot = url_old_dot if url_old_dot else OLD_DOT_URL

    if expensify_dot == "NewDot":
        if await check_if_logged_in(page=page, url=url_new_dot):
            return
        await sign_up_new_dot(page=page, email=email)
    elif expensify_dot == "OldDot":
        if await check_if_logged_in(page=page, url=url_old_dot):
            return
        await sign_up_old_dot(page=page, email=email)
    else:
        raise ValueError("Invalid Expensify dot provided. Please provide either 'NewDot' or 'OldDot'.")

# Old Issue Sign Up workaround
async def old_issue_sign_up(page: Page, email: str, password: str, url_new_dot: str=None, url_old_dot: str=None, mock_otp: bool=False):
    """
    Workaround for the old issue where the user signs up to the OldDot and signs in to the NewDot.
    """
    # Sign up to OldDot
    await sign_up(page=page, expensify_dot="OldDot", email=email, url_old_dot=url_old_dot)
    # Sign in to NewDot
    await sign_in(page=page, expensify_dot="NewDot", email=email, password=password, url_new_dot=url_new_dot, mock_otp=mock_otp)


# Complete the onboarding process
async def complete_onboarding(page: Page, first_name: str='John', last_name: str='Doe'):
    
    """
    Complete the onboarding process for a user who is already logged in.
    This function assumes that the user is already logged in and the "What do you want to do today?" dialog box is visible.
    It is the responsibility of the caller to ensure that these conditions are met before calling this function.
    Steps:
    1. Verify that the "What do you want to do today?" dialog box is visible.
    2. Select 'Track and budget expenses' on the onboarding page and click Continue.
    3. Enter the first name and last name, then click Continue.
    Args:
        page (Page): The Playwright Page object representing the browser page.
    Raises:
        AssertionError: If the "What do you want to do today?" dialog box is not visible.
    """ 
    
    await expect(page.locator("text=What do you want to do today?")).to_be_visible()
        
    # Select 'Track and budget expenses' in onobarding page and click Continue
    await page.locator("text='Track and budget expenses'").click()
    await page.get_by_role("button", name="Continue").click()

    # Enter first name, last name and click continue
    await page.locator('input[name="fname"]').fill(first_name)
    await page.locator('input[name="lname"]').fill(last_name)
    await page.get_by_role("button", name="Continue").last.click()