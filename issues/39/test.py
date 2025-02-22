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
EMAIL = "turingvidhant+114@gmail.com"
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
        amount="100"


        workspace_chat = page.locator('button[aria-label="Navigates to a chat"]', has_text="Turing Vidhant+114's Workspace")
        expect(workspace_chat).to_be_visible()
        workspace_chat.click()
        page.wait_for_timeout(2000) 


        plus_create_icon = page.locator('button[aria-label="Create"]').last
        expect(plus_create_icon).to_be_visible()
        plus_create_icon.click()
        page.wait_for_timeout(2000) 

        submit_expense_button = page.locator('div[aria-label="Submit expense"]')
        expect(submit_expense_button).to_be_visible()
        submit_expense_button.click()
        page.wait_for_timeout(2000) 


        manual_button = page.locator('button[aria-label="Manual"]')
        expect(manual_button).to_be_visible()
        manual_button.click()
        page.wait_for_timeout(2000) 

        page.locator('input[role="presentation"]').fill(amount)


        next_button = page.locator('button[data-listener="Enter"]', has_text="Next").first
        expect(next_button).to_be_visible()
        next_button.click()
        page.wait_for_timeout(2000) 


        merchant_field = page.locator('div[role="menuitem"]', has_text="Merchant")
        expect(merchant_field).to_be_visible()
        merchant_field.click()
        page.wait_for_timeout(2000) 

        page.locator('input[aria-label="Merchant"]').fill("Test Merchant")

        save_button = page.locator('button', has_text="Save")
        expect(save_button).to_be_visible()
        save_button.click()
        page.wait_for_timeout(2000) 


        save_button = page.locator('button[data-listener="Enter"]', has_text="Submit")
        expect(save_button).to_be_visible()
        save_button.click()
        page.wait_for_timeout(2000) 


        new_workspace_chat = page.locator('button[aria-label="Navigates to a chat"]', has_text="Turing Vidhant+114's Workspace")
        expect(new_workspace_chat).to_be_visible()
        new_workspace_chat.click()
        page.wait_for_timeout(2000)  
        
        view_details = page.locator('button[aria-label="View details"]').last
        expect(view_details).to_be_visible()
        view_details.click()
        

        page.get_by_role("textbox").type(':eye:', delay=100)
        page.wait_for_timeout(2000)   
        
        

        smile_emoji = page.locator('div[aria-label="smile+1}"]')
        page.wait_for_timeout(2000) 

        if smile_emoji.is_visible():
            assert False, "Emoji suggestion does not auto close after inserting emoji."
        else:
            assert True, "Emoji suggestion auto close after inserting emoji."
        

        page.wait_for_timeout(1500)
        page.close()
        browser.close()