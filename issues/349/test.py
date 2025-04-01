import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import re
import time
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page
import imaplib
import email
from email.header import decode_header
from json import tool

USER_EMAIL = "playwright2user+105@gmail.com"
PASSWORD = "zehr mglm gizg gjcc"

def fetch_verification_code_from_email(user_email, password, retries=10, delay=10):
    """
    Fetch the OTP code from the latest email.
    """
    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    imap.login(user_email, password)

    for attempt in range(retries):
        imap.select("inbox")
        status, messages = imap.search(
            None, '(UNSEEN SUBJECT "Expensify magic sign-in code")'
        )
        if status == "OK":
            email_ids = messages[0].split()

            if email_ids:

                latest_email_id = email_ids[-1]
                status, msg_data = imap.fetch(latest_email_id, "(RFC822)")

                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])


                        if msg.is_multipart():
                            for part in msg.walk():
                                content_type = part.get_content_type()
                                if content_type == "text/plain":
                                    body = part.get_payload(decode=True).decode()
                                    match = re.search(r'\b\d{6}\b', body)
                                    if match:
                                        otp_code = match.group(0)
                                        imap.logout()
                                        return otp_code
                        else:

                            body = msg.get_payload(decode=True).decode()
                            match = re.search(r'\b\d{6}\b', body)
                            if match:
                                otp_code = match.group(0)
                                imap.logout()
                                return otp_code
            else:
                print("No new emails found. Retrying...")
                otp_code="123456"
                return otp_code
        else:
            print("Failed to retrieve emails. Retrying...")


        time.sleep(delay)

    imap.logout()
    raise Exception("Max retries reached. No magic code email found.")

def login_user(p: PlaywrightContextManager, first_name="Milan", last_name="T") -> tuple[Browser, Page, str]:

    browser = p.chromium.launch(
            headless=True,  # Set to False to see the browser
            args=[
                "--disable-web-security",  # Disable CORS (for testing only)
                "--disable-features=IsolateOrigins,site-per-process"
            ])
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    user_email = USER_EMAIL
    first_name = 'You can choose first name of your choice and paste'
    last_name = 'You can choose last name of your choice and paste'


    page.goto('https://dev.new.expensify.com:8082/') 


    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(2000)

    verification_code = fetch_verification_code_from_email(user_email, PASSWORD)
    

    otp_input = page.locator("[autocomplete='one-time-code']")
    expect(otp_input).to_be_visible()
    otp_input.fill(verification_code)


    try: 
        page.locator('button[tabindex="0"]').click() 
        page.wait_for_timeout(4000)
    except Exception:
        pass

    return browser, page, user_email


def test_dropdown_select_button():
    with sync_playwright() as p:
        
        

        browser, page, user_email = login_user(p)


        page.wait_for_timeout(2000)

        page.locator('button[aria-label="My settings"]').click()
        page.locator('div[aria-label="Workspaces"]').click()



        page.get_by_role('button', name='New workspace').nth(0).click()
        

        back_arrow_button = page.locator('button[aria-label="Back"]')
        expect(back_arrow_button).to_be_visible()
        back_arrow_button.click()

        inbox_menu = page.locator('button[aria-label="Inbox"]')
        expect(inbox_menu).to_be_visible()
        inbox_menu.click()
        page.wait_for_timeout(2000)
        
        

        chat_1 = page.locator('button[aria-label="Navigates to a chat"]').nth(1)
        expect(chat_1).to_be_visible()
        chat_1.click()
        
        chat_2 = page.locator('button[aria-label="Navigates to a chat"]').nth(2)
        expect(chat_2).to_be_visible()
        chat_2.click()
        page.wait_for_timeout(2000)
        page.wait_for_timeout(2000)
        
        tooltip_div = page.locator('div[data-testid="DisplayNamesWithTooltip"]').nth(1)
        span_element = tooltip_div.locator('span').get_by_text('....')
        span_element.hover()
        page.wait_for_timeout(3000)

        

        tooltip = page.locator('span:has-text("You can choose first name of your choice and paste (you)")').last
        text_align_property = tooltip.evaluate("element => window.getComputedStyle(element).textAlign")
        page.wait_for_timeout(2000)

        if text_align_property == 'center':
            assert True, 'Tooltip is center aligned.'
        else:
           assert False, 'Tooltip is not center aligned'
            
        browser.close()

