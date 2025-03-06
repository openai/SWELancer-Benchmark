import logging
import sys

from playwright.sync_api import sync_playwright, expect
from playwright._impl._browser import Browser
from playwright._impl._page import Page
from playwright.sync_api._context_manager import PlaywrightContextManager
import re
import time
import imaplib
import email
import random

# Expensify app URL
NEWDOT_URL = "https://dev.new.expensify.com:8082"
OLDDOT_URL = "http://127.0.0.1:9000/"

# Logger
logging.basicConfig(level=logging.INFO, stream=sys.stdout, format="%(message)s")
LOGGER = logging.getLogger(__name__)

class IMAPOTPExtractor:
    def __init__(self, email_address, password):
        # Validate email and password input
        if not self._validate_email(email_address):
            raise ValueError("Invalid email address format.")
        self.original_email = email_address
        self.password = password

        # Generate new random email using "+" prefix
        random_suffix = random.randint(1000, 9999)
        current_timestamp = int(time.time())
        random_suffix = f'{current_timestamp}{random_suffix}'
        self.new_email = self._generate_new_email(email_address, random_suffix)
    
    def _validate_email(self, email_address):
        # Simple email validation
        return bool(re.match(r'[^@]+@[^@]+\.[^@]+', email_address))
    
    def _generate_new_email(self, email_address, suffix):
        # Add random number suffix to the email before the "@" symbol
        username, domain = email_address.split('@')
        return f'{username}+{suffix}@{domain}'

    def get_new_email(self):
        # Return the generated email with "+" suffix
        return self.new_email
    
    def check_for_otp(self):
        # Connect to the Gmail server using IMAP
        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(self.original_email, self.password)
            mail.select("inbox")

            # Fetch all unread emails
            status, messages = mail.search(None, "UNSEEN")
            if status != "OK":
                print("No unread emails found.")
                return None

            email_ids = messages[0].split()
            # Start from the latest email by reversing the list
            email_ids = email_ids[::-1]  # Reverse order to process latest first

            # Iterate over each email until OTP is found
            for email_id in email_ids:
                # Fetch the email by ID
                status, msg_data = mail.fetch(email_id, '(RFC822)')
                if status != "OK":
                    print("Error fetching email.")
                    continue

                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])

                        # Check if the To address matches the generated new email
                        if msg["To"] == self.new_email:
                            # Extract OTP from the email body
                            otp_code = self._extract_otp_from_email(msg)
                            if otp_code:
                                # Delete the email containing the OTP
                                mail.store(email_id, '+FLAGS', '\\Deleted')
                                mail.expunge()  # Permanently removes deleted emails from the mailbox
                                
                                # Logout and return OTP
                                mail.close()
                                mail.logout()
                                return otp_code

            # Logout if OTP not found in unread emails
            mail.close()
            mail.logout()
            print("No OTP found in unread emails.")
            return None
        
        except imaplib.IMAP4.error:
            print("Failed to connect to Gmail. Please check your email address or password.")
            return None

    def _extract_otp_from_email(self, msg):
        # Extract OTP code from the email content
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
        # Find a 6-digit code in the email body
        match = re.search(r'\b\d{6}\b', text)
        return match.group(0) if match else None

def submit_expense_in_workspace_chat(
    browser: Browser, 
    page: Page, 
    user_email: str, 
    amount: str = "1000"
) -> tuple[Browser, Page, str]:
    # Click on workspace chat
    workspace_chat = page.locator('button[aria-label="Navigates to a chat"]', has_text="Milan T's Workspace").nth(0)
    expect(workspace_chat).to_be_visible()
    workspace_chat.click()
    page.wait_for_timeout(1000)
 
    # Click on "+" icon and click submit expense
    plus_create_icon = page.locator('button[aria-label="Create"]').last
    expect(plus_create_icon).to_be_visible()
    plus_create_icon.click()
    page.wait_for_timeout(2000)

    try:
        expect(page.locator('div[aria-label="Submit expense"]')).to_be_visible()
        page.locator('div[aria-label="Submit expense"]').click()
    
    except:
        page.get_by_label("Create expense").click()
    
    page.wait_for_timeout(1000)

    # Click on "Manual" button and enter amount
    page.get_by_label("Manual").click()
    page.wait_for_timeout(1000)

    page.locator('input[role="presentation"]').fill(amount)

    # Click on Next button
    next_button = page.locator('button[data-listener="Enter"]', has_text="Next").first
    expect(next_button).to_be_visible()
    next_button.click()
    page.wait_for_timeout(1000)


    # Add the description
    page.locator('div[role="menuitem"]', has_text="Description").click()
    page.locator('div[role="textbox"][aria-label="What\'s it for?"]').fill("Descrip")
    page.locator('button', has_text="Save").click()


    # Add merchant details
    page.locator('div[role="menuitem"]', has_text="Merchant").click()
    page.wait_for_timeout(1000)
    page.locator('input[aria-label="Merchant"]').fill("Merch")

    save_button = page.locator('button', has_text="Save")
    expect(save_button).to_be_visible()
    save_button.click()
    page.wait_for_timeout(1000)

    # Submit the expense
    save_button = page.locator('button[data-listener="Enter"]', has_text="Submit")
    expect(save_button).to_be_visible()
    save_button.click()
    page.wait_for_timeout(1000)

    return browser, page, user_email

def login_user(p: PlaywrightContextManager, first_name="Milan", last_name="T") -> tuple[Browser, Page, str]:
    email_address = "rgarciatammy4@gmail.com"
    password = ""
    account = IMAPOTPExtractor(email_address, password)
    new_email_address = account.get_new_email()

    # Launch chromiun and open new page
    browser = p.chromium.launch(headless=False, args=[
        "--ignore-certificate-errors",
        "--disable-web-security",
        "--disable-features=IsolateOrigins,site-per-process"
    ],
    proxy={"server": "http://localhost:8080"})
    context = browser.new_context(viewport={"width": 320, "height": 812},
        is_mobile=True,
        has_touch=True)
    page = context.new_page()

    # Step 1: Open expensify url
    page.goto('https://dev.new.expensify.com:8082/') 

    # Step 2: Enter email and click continue
    page.locator('input[type="email"]').fill(new_email_address)
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(1000)

    # Step 3: Click join button
    page.get_by_role("button", name="Join").click()
        
    # Step 4: Select 'Track and budget expenses' in onobarding page and click Continue
    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()
    page.wait_for_timeout(1000)

    # Step 5: Enter first name, last name and click continue
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()
    page.wait_for_timeout(1000)

    return browser, page, new_email_address

def test_tag_long_press_issue():
    with sync_playwright() as pw:
        browser, page, user_email = login_user(pw)
        page.wait_for_timeout(2000)
        page.get_by_label("Back").click()
        page.wait_for_timeout(2000)
        page.get_by_label("Start chat (Floating action)").click()
        page.wait_for_timeout(2000)
        page.get_by_label("New workspace").click()
        page.wait_for_timeout(2000)
        page.get_by_label("More features").click()
        page.wait_for_timeout(2000)
        page.get_by_label("Classify costs and track").click()
        page.wait_for_timeout(2000)
        page.get_by_label("Tags").click()
        page.wait_for_timeout(2000)
        page.get_by_role("button", name="Add tag").click()
        page.wait_for_timeout(2000)
        page.get_by_role("textbox", name="Name").fill("Tag1")
        page.wait_for_timeout(2000)
        page.get_by_role("textbox", name="Name").press("Enter")
        page.wait_for_timeout(2000)
        if(page.get_by_test_id("WorkspaceMoreFeaturesPage").get_by_label("Back").is_visible()):
            page.get_by_test_id("WorkspaceMoreFeaturesPage").get_by_label("Back").click()
        page.get_by_role("button", name="Add tag").click()
        page.wait_for_timeout(2000)
        page.get_by_role("textbox", name="Name").fill("Tag2")
        page.wait_for_timeout(2000)
        page.get_by_role("textbox", name="Name").press("Enter")
        page.wait_for_timeout(2000)
        if(page.get_by_test_id("WorkspaceMoreFeaturesPage").get_by_label("Back").is_visible()):
            page.get_by_test_id("WorkspaceMoreFeaturesPage").get_by_label("Back").click()
        page.get_by_label("Tag1").click()
        page.get_by_label("Tag1").first.hover()
        page.mouse.down()
        page.wait_for_timeout(5000)
        page.mouse.up()
        page.wait_for_timeout(2000)
        expect(page.get_by_text("Enable tag")).to_be_visible()
        expect(page.get_by_text("Select")).not_to_be_visible()

        # Close the browser
        page.close()
        browser.close()