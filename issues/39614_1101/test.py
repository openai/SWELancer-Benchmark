import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import os
import time
import pytest
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page
from playwright.sync_api import sync_playwright, expect
import re, time
import os
import imaplib
import email
import re
import random

NEWDOT_URL = "https://dev.new.expensify.com:8082/"
OLDDOT_URL = "http://localhost:9000/"
EMAIL = "turingvidhant+109@gmail.com"
PASSWORD = "uotx fzkt kfeg dehz"

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
    page.wait_for_timeout(100)

    page.get_by_test_id("WorkspaceSwitcherPage").get_by_role(
        "button", name="New workspace"
    ).click()
    page.wait_for_timeout(100)

    page.locator('div[aria-label="More features"]').click()
    page.wait_for_timeout(100)


    toggle_button = page.locator(f'button[aria-label="{feature}"]')
    if not toggle_button.is_checked():
        toggle_button.click()
        page.wait_for_timeout(100)

    page.locator('div[aria-label="Tags"]').click()
    page.wait_for_timeout(100)


def create_tag(page: Page, tag_name: str):
    page.locator("button", has_text="Add tag").click()
    page.wait_for_timeout(100)

    page.locator('input[aria-label="Name"]').fill(tag_name)
    page.wait_for_timeout(100)

    page.locator('button[data-listener="Enter"]', has_text="Save").click()
    page.wait_for_timeout(100)


def select_all_tags(page: Page, check: bool):
    select_all = page.locator('div[aria-label="Select all"][role="checkbox"]')
    if (not select_all.is_checked() and check) or (
        select_all.is_checked() and not check
    ):
        select_all.click()
        page.wait_for_timeout(100)

    if check:
        return page.locator('button[data-listener="Enter"]').inner_text()
    else:
        return None


def delete_tag(page: Page, tag_name: str):
    page.locator(f'button[id="{tag_name}"]').click()
    page.wait_for_timeout(100)

    page.locator('div[aria-label="Delete"]').click()
    page.wait_for_timeout(100)

    page.locator('button[data-listener="Enter"]').click()
    page.wait_for_timeout(100)

def new_dot_login(page, email):
    page.goto(NEWDOT_URL)  
    page.locator('input[type="email"]').fill(email)
    page.wait_for_timeout(3000)
    page.get_by_role("button", name="Continue").nth(0).click()
    page.wait_for_timeout(3000)
    gmail_account_helper.set_new_email(email)
    otp = gmail_account_helper.check_for_otp()
    page.locator('input[data-testid="validateCode"]').fill("123456")
    try:
        page.get_by_role("button", name="Sign In").click()
    except:
        pass

def launch_browser(pw, headless=True, device=None, geolocation=None):
    """
    Launch the browser.
    """
    browser = pw.chromium.launch(headless=headless)
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

    more_features_button = page.locator('div[aria-label="More features"]')
    expect(more_features_button).to_be_visible()
    more_features_button.click()
    page.wait_for_timeout(1000)


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

    page.get_by_label("Workspaces").click()
    page.get_by_label("New workspace").click()
    page.wait_for_timeout(500)

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
        browser = p.chromium.launch(headless=True, args=[
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ])

        first_user_context = browser.new_context(ignore_https_errors=True)
        page = first_user_context.new_page()        
        page.wait_for_timeout(3000)

        new_dot_login(page, EMAIL)
        page.wait_for_timeout(3000)
        
        start_chat_button = page.get_by_label("Start chat (Floating action)")
        start_chat_button.click()
        
        page.get_by_label("Workspaces").click()
        page.get_by_label("New workspace").click()
        page.wait_for_timeout(500)
        

        features_text_element = page.locator('div[dir="auto"]', has_text="More features")
        features_text_element.click()
        

        documement_button = page.get_by_label("Document and reclaim eligible")
        documement_button.click()

        taxes_button = page.get_by_test_id("WorkspaceInitialPage").get_by_label("Taxes")
        taxes_button.click()
        

        add_rate = page.get_by_role("button", name="Add rate")
        add_rate.click()
        
        tax_name_button = page.get_by_test_id("WorkspaceCreateTaxPage").get_by_text("Name")
        tax_name_button.click()
        page.get_by_role("textbox", name="Name").fill("1/")
        
        save_button = page.get_by_test_id("TextSelectorModal").get_by_role("button", name="Save")
        save_button.click()

        tax_value_button = page.get_by_text("Value")
        tax_value_button.click()
        page.get_by_placeholder("0").fill("1")
        save_button = page.get_by_test_id("AmountSelectorModal").get_by_role("button", name="Save")
        save_button.click()

        save_button = page.get_by_role("button", name="Save").last
        save_button.click()
        page.locator("button").filter(has_text="/1%").click()
        

        element = page.locator('div[dir="auto"]', has_text="Hmm... it's not here")
        expect(element).not_to_be_visible()

        page.wait_for_timeout(1500)
        page.close()
        browser.close()