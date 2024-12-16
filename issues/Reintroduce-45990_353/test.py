import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
from playwright.sync_api import sync_playwright, expect
from playwright._impl._browser import Browser
from playwright._impl._page import Page
from playwright.sync_api import sync_playwright, expect
import re, time
import imaplib
import email
import re
import random

NEWDOT_URL = "https://dev.new.expensify.com:8082/"
OLDDOT_URL = "http://localhost:9000/"

EMAIL = "totherandomuser+45990@gmail.com"
PASSWORD = "umei djwi bfmp jntm"

class IMAPOTPExtractor:
    def __init__(self, email_address, password):
        if not self._validate_email(email_address):
            raise ValueError("Invalid email address format.")
        self.original_email = email_address
        self.password = password

        random_suffix = random.randint(1000, 9999)
        current_timestamp = int(time.time())
        random_suffix = f"{current_timestamp}{random_suffix}"
    
    def _validate_email(self, email_address):
        return bool(re.match(r"[^@]+@[^@]+\.[^@]+", email_address))
    
    def set_new_email(self, email):
        self.new_email = email
    
    def check_for_otp(self):
        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(self.original_email, self.password)
            mail.select("inbox")
            
            status, messages = mail.search(None, "UNSEEN")
            if status != "OK":
                return None
            
            email_ids = messages[0].split()            
            email_ids = email_ids[::-1]

            for email_id in email_ids:
                status, msg_data = mail.fetch(email_id, '(RFC822)')
                if status != "OK":
                    continue
                
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])

                        if self.new_email in msg["To"]:
                            otp_code = self._extract_otp_from_email(msg)
                            if otp_code:
                                mail.store(email_id, '+FLAGS', '\\Deleted')
                                mail.expunge()
                                mail.close()
                                mail.logout()
                                return otp_code
            
            mail.close()
            mail.logout()
            return None

        except imaplib.IMAP4.error:
            return None

    def _extract_otp_from_email(self, msg):
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    email_body = part.get_payload(decode=True).decode()
                    otp_code = self._extract_otp(email_body)
                    if otp_code:
                        return otp_code
        else:
            email_body = msg.get_payload(decode=True).decode()
            otp_code = self._extract_otp(email_body)
            if otp_code:
                return otp_code
        return None

    def _extract_otp(self, text):
        match = re.search(r"\b\d{6}\b", text)
        return match.group(0) if match else None

gmail_account_helper = IMAPOTPExtractor(EMAIL, PASSWORD)

def create_workspace_and_enable_feature(page: Page, feature: str):
    """
    Creates a new workspace and enables a specified feature.

    Args:
        page (Page): The Playwright page object.
        feature (str): The feature to enable (e.g., "Invoices").
    """
    page.locator('button[aria-label="Workspaces"]').click()
    time.sleep(0.1)

    page.get_by_test_id("WorkspaceSwitcherPage").get_by_role(
        "button", name="New workspace"
    ).click()
    time.sleep(0.1)

    page.locator('div[aria-label="More features"]').click()
    time.sleep(0.1)

    # Toggle feature
    toggle_button = page.locator(f'button[aria-label="{feature}"]')
    if not toggle_button.is_checked():
        toggle_button.click()
        time.sleep(0.1)

    page.locator('div[aria-label="Tags"]').click()
    time.sleep(0.1)


def create_tag(page: Page, tag_name: str):
    page.locator("button", has_text="Add tag").click()
    time.sleep(0.1)

    page.locator('input[aria-label="Name"]').fill(tag_name)
    time.sleep(0.1)

    page.locator('button[data-listener="Enter"]', has_text="Save").click()
    time.sleep(0.1)


def select_all_tags(page: Page, check: bool):
    select_all = page.locator('div[aria-label="Select all"][role="checkbox"]')
    if (not select_all.is_checked() and check) or (
        select_all.is_checked() and not check
    ):
        select_all.click()
        time.sleep(0.1)

    if check:
        return page.locator('button[data-listener="Enter"]').inner_text()
    else:
        return None


def delete_tag(page: Page, tag_name: str):
    page.locator(f'button[id="{tag_name}"]').click()
    time.sleep(0.1)

    page.locator('div[aria-label="Delete"]').click()
    time.sleep(0.1)

    page.locator('button[data-listener="Enter"]').click()
    time.sleep(0.1)

def new_dot_login(page, email):
    page.goto(NEWDOT_URL)  
    page.locator('input[type="email"]').fill(email)
    page.wait_for_timeout(3000)
    page.get_by_role("button", name="Continue").nth(0).click()
    page.wait_for_timeout(3000)
    # gmail_account_helper.set_new_email(email)
    # otp = gmail_account_helper.check_for_otp()
    otp = "123456"
    page.locator('input[data-testid="validateCode"]').fill(otp)
    try:
        page.get_by_role("button", name="Sign In").click()
    except:
        pass

def launch_browser(pw, headless=True, device=None, geolocation=None):
    """
    Launch the browser.
    """
    browser = pw.chromium.launch(headless=headless, slow_mo=500, args=[
                    "--disable-web-security",
                    "--disable-features=IsolateOrigins,site-per-process",]
                    )
    context_args = {}
    if device:
        context_args.update(pw.devices[device])
    if geolocation:
        context_args["geolocation"] = geolocation
        context_args["permissions"] = ["geolocation"]
    context = browser.new_context(**context_args)
    page = context.new_page()
    return browser, context, page
    

def enable_report_fields(
    browser: Browser, 
    page: Page, 
    user_email: str, 
):
    # Click on more features
    more_features_button = page.locator('div[aria-label="More features"]')
    expect(more_features_button).to_be_visible()
    more_features_button.click()
    page.wait_for_timeout(1000)

    # Enable report fields
    report_fields_switch = page.locator('button[aria-label="Set up custom fields for spend."]')
    expect(report_fields_switch).to_be_visible()
    report_fields_switch.click()
    page.wait_for_timeout(1000)

    try:
        page.locator('button[data-tag="pressable"]', has_text="Upgrade").last.click()
        page.wait_for_timeout(1000)

        page.locator('button[data-tag="pressable"]', has_text="Got it, thanks").last.click()
        page.wait_for_timeout(1000)
    except Exception:
        pass

    report_fields_button = page.locator('div[aria-label="Report fields"][role="menuitem"]')
    expect(report_fields_button).to_be_visible()
    report_fields_button.click()
    page.wait_for_timeout(1000)

    return browser, page, user_email


def create_new_workspace(
    browser: Browser, 
    page: Page, 
    user_email: str, 
) -> tuple[Browser, Page, str]:
    # Step 1: Click on + icon and click on "New workspace"
    plus_icon = page.locator('button[aria-label="Start chat (Floating action)"]')
    expect(plus_icon).to_be_visible()
    plus_icon.click()
    page.wait_for_timeout(1000)

    new_workspace_button = page.locator('div[aria-label="New workspace"]')
    expect(new_workspace_button).to_be_visible()
    new_workspace_button.click()
    page.wait_for_timeout(1000)

    return browser, page, user_email


def add_report_field_list_value(
    page: Page, 
    value: str, 
) -> Page:
    page.locator('button', has_text="Add value").last.click()
    page.wait_for_timeout(1000)
    
    page.locator('input[aria-label="Value"]').last.fill(value)
    page.wait_for_timeout(1000)

    page.locator('button[data-listener="Enter"]', has_text="Save").last.click()
    page.wait_for_timeout(1000)

    return page


def test_expensify():
     with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, slow_mo=500, args=[
                    "--disable-web-security",
                    "--disable-features=IsolateOrigins,site-per-process",]
                    )

        first_user_context = browser.new_context(ignore_https_errors=True)
        page = first_user_context.new_page()        
        page.wait_for_timeout(3000)

        new_dot_login(page, EMAIL)
        page.wait_for_timeout(3000)
        
        # Step 2: Create a new workspace and enable report fields
        browser, page, user_email = create_new_workspace(browser, page, EMAIL)
        browser, page, user_email = enable_report_fields(browser, page, EMAIL)

        # Step 3: Add list field
        page.locator('button', has_text="Add field").last.click()
        page.wait_for_timeout(1000)

        page.locator('div[role="menuitem"]', has_text="Name").last.click()
        page.wait_for_timeout(1000)

        page.locator('input[aria-label="Name"]').last.fill("MyListReportField")
        page.wait_for_timeout(1000)

        page.locator('button[data-listener="Enter"]', has_text="Save").last.click()
        page.wait_for_timeout(1000)

        page.locator('div[role="menuitem"]', has_text="Type").last.click()
        page.wait_for_timeout(1000)

        page.locator('button[aria-label="List"]', has_text="List").last.click()
        page.wait_for_timeout(1000)

        # Step 4: Create list values
        page.locator('div[role="menuitem"][tabindex="0"]', has_text="List values").last.click()
        page.wait_for_timeout(1000)

        page = add_report_field_list_value(page, "TestValueA")
        page = add_report_field_list_value(page, "TestValueB")
        page = add_report_field_list_value(page, "TestValueC")

        page.locator('button[aria-label="Back"]').last.click()
        page.wait_for_timeout(1000)
        
        # Step 5: Validate initial values menuitem is visible below the list values
        list_values_menuitem = page.locator('div[role="menuitem"][tabindex="0"]', has_text="List values").last
        expect(list_values_menuitem).to_be_visible()
        list_values_bounding_box = list_values_menuitem.bounding_box()

        initial_values_menuitem = page.locator('div[role="menuitem"][tabindex="0"]', has_text="Initial value").last
        expect(initial_values_menuitem).to_be_visible()
        initial_values_bounding_box = initial_values_menuitem.bounding_box()

        assert list_values_bounding_box['y'] < initial_values_bounding_box['y']

        # Step 6: Validate created values are visible as comma separated list
        list_values = page.locator('div', has_text="TestValueA, TestValueB, TestValueC").last
        expect(list_values).to_be_visible()

        page.wait_for_timeout(1500)
        page.close()
        browser.close()
