import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)


import logging
import sys

from playwright.sync_api import sync_playwright, expect


# Expensify app URL
EXPENSIFY_URL = "http://localhost:8082/"

# Email login credentials
EMAIL_USERNAME = "naturesv057@gmail.com"
EMAIL_PASSWORD = "hyjk ilxi pnom oret"

# Logger
logging.basicConfig(level=logging.INFO, stream=sys.stdout, format="%(message)s")
LOGGER = logging.getLogger(__name__)

def generate_user_email(EMAIL_USERNAME_POSTFIX):
    """
    Generate an email address for a user login.
    """
    temp = EMAIL_USERNAME.rsplit("@", 1)
    username = temp[0].strip()
    domain = temp[1].strip()
    return f"{username}+{EMAIL_USERNAME_POSTFIX}@{domain}"


def launch_browser(pw, headless=True, device=None, geolocation=None):
    """
    Launch the browser.
    """
    browser = pw.chromium.launch(channel="chrome", headless=True, slow_mo=2100, args=[
            "--ignore-certificate-errors",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ])
    context_args = {}
    if device:
        context_args.update(pw.devices[device])
    if geolocation:
        context_args["geolocation"] = geolocation
        context_args["permissions"] = ["geolocation"]
    context = browser.new_context(**context_args)
    page = context.new_page()
    return browser, context, page


def login_user(page, email, first_name="John", last_name="Doe"):
    """
    Login to the Expensify app and complete the onboarding.
    """
    # Clear the email inbox

    # Open the Expensify app
    page.goto(EXPENSIFY_URL)

    # Login user
    page.get_by_role("textbox", name="Phone or email").fill(email)
    page.locator("div", has_text="Continue").last.click()
    
    
    # Enter the OTP code
    page.keyboard.type("132203")


def test_main():
    """
    Demonstrate the Expensify app email login verification.
    """
    with sync_playwright() as pw:
        #Step 1: Login user1
        email1 = generate_user_email("28863_10")
        LOGGER.info("User email %s", email1)
        browser1, context1, page1 = launch_browser(pw)
        login_user(page1, email1)
        page1.wait_for_timeout(5000)
        LOGGER.info("User logged in successfully")


        email2 = generate_user_email("28863_12")
        LOGGER.info("User email %s", email2)
        browser2, context2, page2 = launch_browser(pw)
        login_user(page2, email2)
        page2.wait_for_timeout(5000)
        LOGGER.info("User1 logged in successfully")


        #User1 sends message to User2
        page1.get_by_label("Search").click()
        page1.get_by_role("textbox", name="Name, email, or phone number").fill(email2)        
        page1.get_by_role("textbox", name="Name, email, or phone number").press("Tab")
        page1.wait_for_timeout(1000)
        page1.locator("body").press("Enter")
        page1.wait_for_timeout(1000)
        page1.get_by_role("textbox", name="Write something...").fill("Message user 1")
        page1.get_by_role("textbox").press("Enter")

        page1.wait_for_timeout(5000)

        #Respond by second user
        page2.get_by_label("Navigates to a chat").nth(2).click()
        page2.get_by_role("textbox", name="Write something...").click()
        page2.get_by_role("textbox", name="Write something...").fill("Message user 2")
        page2.get_by_role("textbox").press("Enter")


        #clcik on back button to regenerate the issue
        page1.locator("span").filter(has_text="Message user 2").last.click(button="right")
        page1.wait_for_timeout(1000)
        page1.get_by_text("Flag as offensive").click()
        page1.wait_for_timeout(1000)

        # back button is overlapping here
        try:
            page1.locator('div[aria-label="Back"]').click()
        except:
            page1.get_by_label("Back").nth(1).click()

        expect(page1.locator('div[aria-label="Back"]')).not_to_be_visible()

        # Cleanup
        page1.close()
        context1.close()
        browser1.close()
        page2.close()
        context2.close()
        browser2.close()
