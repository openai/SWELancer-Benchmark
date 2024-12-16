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
EMAIL = "turingvidhant+105@gmail.com"
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

def invite_user(
    browser: Browser, 
    page: Page, 
    user_email: str = "abcd@gmail.com", 
) -> tuple[Browser, Page, str]:
    # Step 1: Click on + icon and click on "New workspace"
    plus_icon = page.locator('button[aria-label="Start chat (Floating action)"]')
    expect(plus_icon).to_be_visible()
    plus_icon.click()
    page.wait_for_timeout(1000)

    start_chat_button = page.locator('div[aria-label="Start chat"]')
    expect(start_chat_button).to_be_visible()
    start_chat_button.click()
    page.wait_for_timeout(1000)

    # Step 2: Enter email id and click on user tab
    page.locator('input[aria-label="Name, email, or phone number"]').fill(user_email)
    page.wait_for_timeout(5000)
    user_tab = page.locator(f'button[aria-label="{user_email}"]')
    expect(user_tab).to_be_visible()
    user_tab.click()
    page.wait_for_timeout(2000)

    return browser, page, user_email


def select_currency(page, currency: str = "USD", currency_symbol: str = "$"):
    currency_icon = page.locator('button[aria-label="Select a currency"]').last
    expect(currency_icon).to_be_visible()
    currency_icon.click()
    page.wait_for_timeout(1000)

    page.locator('input[aria-label="Search"]').fill(currency)
    page.wait_for_timeout(1000)

    currency_button = page.locator(f'button[aria-label="{currency} - {currency_symbol}"]').last
    expect(currency_button).to_be_visible()
    currency_button.click()
    page.wait_for_timeout(1000)

    return page


def pay_to_user(
    browser: Browser, 
    page: Page, 
    user_email: str, 
    amount: str = "500",
) -> tuple[Browser, Page, str]:
    # Step 1: Click on "+" icon and click on Pay user
    plus_create_icon = page.locator('button[aria-label="Create"]').last
    expect(plus_create_icon).to_be_visible()
    plus_create_icon.click()
    page.wait_for_timeout(1000)

    pay_user_button = page.locator(f'div[aria-label="Pay "][role="menuitem"]')
    expect(pay_user_button).to_be_visible()
    pay_user_button.click()
    page.wait_for_timeout(1000)

    # Step 3: Select currency and Enter amount
    page = select_currency(page, currency="USD", currency_symbol="$")
    page.locator('input[role="presentation"]').fill(amount)

    # Step 4: Click on Next button
    next_button = page.locator('button[data-listener="Enter"]', has_text="Next").last
    expect(next_button).to_be_visible()
    next_button.click()
    page.wait_for_timeout(1000)

    # Step 5: Click on pay elsewhere
    arrow_button = page.locator('button').last
    expect(arrow_button).to_be_visible()
    arrow_button.click()
    page.wait_for_timeout(1000)

    pay_elsewhere_menuitem = page.locator('div[aria-label="Pay elsewhere"][role="menuitem"]')
    expect(pay_elsewhere_menuitem).to_be_visible()
    pay_elsewhere_menuitem.click()
    page.wait_for_timeout(1000)

    pay_elsewhere_button = page.locator('button', has_text="Pay elsewhere")
    expect(pay_elsewhere_button).to_be_visible()
    pay_elsewhere_button.click()
    page.wait_for_timeout(2000)

    return browser, page, user_email


def force_offline_mode(
    browser: Browser, 
    page: Page, 
    user_email: str, 
) -> tuple[Browser, Page, str]:
    my_settings_button = page.locator('button[aria-label="My settings"]')
    expect(my_settings_button).to_be_visible()
    my_settings_button.click()
    page.wait_for_timeout(1000)

    troubleshoot_button = page.locator('div[aria-label="Troubleshoot"]')
    expect(troubleshoot_button).to_be_visible()
    troubleshoot_button.click()
    time.sleep(1)

    offline_button = page.locator('button[aria-label="Force offline"]')
    expect(offline_button).to_be_visible()
    offline_button.click()
    time.sleep(1)

    return browser, page, user_email

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

        browser, page, user_email = force_offline_mode(browser, page, EMAIL)

        # Step 2: Invite user 
        browser, page, invited_user_email = invite_user(browser, page)

        # Step 3: Pay newly invited user
        browser, page, invited_user_email = pay_to_user(browser, page, invited_user_email)

        # Step 4: Open transaction thread
        paid_transaction = page.locator('button[aria-label="View details"]').last
        expect(paid_transaction).to_be_visible()
        paid_transaction.click()
        page.wait_for_timeout(2000)

        # Step 5: Right click on paid system message 
        incorrect_paid_amount = page.locator('div', has_text="$50,000.00")
        expect(incorrect_paid_amount).not_to_be_visible()

        correct_paid_amount = page.locator('span', has_text="paid $500.00 elsewhere").last
        expect(correct_paid_amount).to_be_visible()


        page.wait_for_timeout(1500)
        page.close()
        browser.close()