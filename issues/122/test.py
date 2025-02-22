import time
from playwright.sync_api import Playwright, BrowserContext, Page, sync_playwright, expect
import pytest

from utils.email_handler import EmailHandler


NEWDOT_URL = "https://dev.new.expensify.com:8082/"
EMAIL_ADDRESS = "t56826807@gmail.com"
PASSWORD = "wxck tsaw ocna tkfd"
FIRST_NAME = "D"
LAST_NAME = "C"
MOBILE_DEVICE = "iPhone 12 Pro"


def generate_random_email(base_email=EMAIL_ADDRESS, seed=None):
    if seed is None:
        seed = int(time.time())
    email_user, domain = base_email.split('@')
    return f"{email_user}+{seed}@{domain}"


@pytest.fixture(scope='session')
def playwright_instance():
    with sync_playwright() as playwright:
        yield playwright


@pytest.fixture(scope='session')
def context(playwright_instance: Playwright, mobile_device: str = MOBILE_DEVICE):
    browser = playwright_instance.chromium.launch(
        proxy = {"server": "http://localhost:8080"}, headless = False, args = ["--no-sandbox", "--disable-dev-shm-usage", "--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"], slow_mo = 500, channel = "chromium")
    device_profile = playwright_instance.devices[mobile_device] if mobile_device else {}
    context = browser.new_context(**device_profile)
    yield context
    browser.close()


@pytest.fixture(scope='function')
def page(context: BrowserContext):
    page = context.new_page()
    yield page
    context.close()


def login_user(page: Page, email: str, password: str, first_name=FIRST_NAME, last_name=LAST_NAME, mock_otp: bool=False):
    try:
        # If the user is already logged in, the inbox should be visible
        expect(page.get_by_label("Inbox")).to_be_visible(timeout=3000)
        return
    except:
        pass

    with EmailHandler(email, password) as email_handler:
        # Clean inbox
        if not mock_otp:
            email_handler.mark_all_unread_as_read()

        # Enter email and click continue
        page.get_by_test_id("username").fill(email)
        page.get_by_role("button", name="Continue").click()

        # Check if we have can join directly or we need a magic code
        join_button = page.get_by_role("button", name="Join")
        validate_code_input = page.get_by_test_id("validateCode")
        expect(join_button.or_(validate_code_input)).to_be_visible()

        if (join_button.is_visible()):
            join_button.click()

            try:
                onboarding_user(page, first_name, last_name)
            except:
                pass
        else:
            # Await OTP
            otp = "123456" if mock_otp else email_handler.read_otp_code()
            validate_code_input.fill(otp)

            # Wait sign in to complete
            page.get_by_text("Please enter the magic code").wait_for(state="hidden")

        try:
            page.get_by_label("Back").click()
        except:
            pass


def onboarding_user(page: Page, first_name=FIRST_NAME, last_name=LAST_NAME):
    expect(page.get_by_text("What do you want to do today?")).to_be_visible(timeout=30000)
    
    # Select 'Track and budget expenses' in onboarding page and click Continue
    activity_text="Track and budget expenses"
    page.get_by_label(activity_text).click()

    # Enter first name, last name and click continue
    page.get_by_role("textbox", name="First name").fill(first_name)
    page.get_by_role("textbox", name="Last name").fill(last_name)
    page.get_by_role("button", name="Continue").last.click()


def test(page: Page):
    # Open expensify url
    page.bring_to_front()
    page.goto(NEWDOT_URL)

    # Login user
    email_address = generate_random_email(seed=1739850017)
    login_user(page, email_address, PASSWORD)

    # Tap on "Settings" on the bottom of the screen.
    page.get_by_label("My settings").click()
    # Tap on "Profile"
    page.get_by_role("menuitem", name="Profile").click()
    # Scroll down to "Date of Birth" and open the tab.
    page.get_by_role("menuitem", name="Date of birth").click()
    # Tap on the year, to open the years list.
    page.get_by_test_id("currentYearButton").click()
    # Use device´s back button to return to calendar.
    page.go_back()
    # Verify you land on the calendar tab again.
    expect(page.get_by_test_id("DateOfBirthPage").get_by_text("Date of birth")).to_be_visible()
