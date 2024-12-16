import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import asyncio
from playwright.async_api import async_playwright, Page, expect
import os
import time
from email.header import decode_header
import time
import re
import imaplib
import email
import logging
from email.header import decode_header

# Load credentials
NEW_DOT_URL = "https://dev.new.expensify.com:8082"
EXPENSIFY_EMAIL = os.getenv("USER_EMAIL", "testingq186+41783@gmail.com")
EXPENSIFY_PASSWORD = os.getenv("PASSWORD", "kkfr hqiv yuxq rbso")
FIRST_NAME = "Testing"
LAST_NAME = "41783"

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def main():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True, args=["--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"],
    proxy={"server": "http://localhost:8080"},
    slow_mo=500)
        context = await browser.new_context(ignore_https_errors=True)
        page = await context.new_page()

        class EmailHandler:
          """
          A class to handle email operations such as cleaning the inbox,
          marking all unread emails as read, and reading OTP codes.
          """

          def __init__(self, user_email, password, imap_server='imap.gmail.com'):
              """
              Initializes the EmailHandler with user credentials and connects to the IMAP server.

              Args:
                  user_email (str): The email address of the user.
                  password (str): The password for the email account.
                  imap_server (str): The IMAP server address. Defaults to 'imap.gmail.com'.
              """
              self.user_email = user_email
              self.password = password
              self.imap_server = imap_server
              self.imap = None

          def __enter__(self):
              """
              Enters the runtime context and logs into the IMAP server.
              """
              self.imap = imaplib.IMAP4_SSL(self.imap_server)
              try:
                  self.imap.login(self.user_email, self.password)
                  logging.info("Logged into IMAP server.")
              except Exception as e:
                  logging.error(f"Failed to login to IMAP server: {e}")
                  raise
              return self

          def __exit__(self, exc_type, exc_value, traceback):
              """
              Exits the runtime context and logs out from the IMAP server.
              """
              if self.imap:
                  self.imap.logout()
                  logging.info("Logged out from IMAP server.")

          def clean_inbox(self):
              """
              Deletes all emails in the inbox.

              WARNING: This action is irreversible.
              """
              logging.warning("Deleting all emails in the inbox.")
              # Select the inbox folder
              status, _ = self.imap.select("INBOX")
              if status != "OK":
                  logging.error("Failed to select INBOX.")
                  return

              # Search for all emails
              status, messages = self.imap.search(None, 'ALL')
              if status != "OK":
                  logging.error("Failed to retrieve emails.")
                  return

              email_ids = messages[0].split()
              if not email_ids:
                  logging.info("No emails to delete.")
                  return

              # Mark all emails for deletion
              for email_id in email_ids:
                  self.imap.store(email_id, '+FLAGS', '\\Deleted')

              # Permanently delete emails marked for deletion
              self.imap.expunge()
              logging.info("All emails deleted from the inbox.")

          def mark_all_unread_as_read(self):
              """
              Marks all unread emails in the inbox as read.
              """
              logging.info("Marking all unread emails as read.")
              # Select the inbox folder
              status, _ = self.imap.select("INBOX")
              if status != "OK":
                  logging.error("Failed to select INBOX.")
                  return

              # Search for unread emails
              status, messages = self.imap.search(None, '(UNSEEN)')
              if status != "OK":
                  logging.error("Failed to retrieve unread emails.")
                  return

              email_ids = messages[0].split()
              if not email_ids:
                  logging.info("No unread emails to mark as read.")
                  return

              # Mark each email as read
              for email_id in email_ids:
                  self.imap.store(email_id, '+FLAGS', '\\Seen')
              logging.info("All unread emails marked as read.")

          def read_otp_code(self, retries=5, delay=6):
              """
              Retrieves the OTP code from unread emails.

              Args:
                  retries (int): Number of retries to attempt fetching the OTP code.
                  delay (int): Delay in seconds between retries.

              Returns:
                  str: The OTP code if found, else None.
              """
              logging.info("Attempting to read OTP code from emails.")
              
              # Loop to retry fetching the OTP for a specified number of attempts
              for i in range(retries):

                  # Search for unread emails with the subject "Expensify magic sign-in code:"
                  self.imap.select("inbox")
                  status, messages = self.imap.search(None, '(UNSEEN SUBJECT "Expensify magic sign-in code:")')

                  # Check if the search was successful
                  if not status == "OK":
                      logging.error(f"Failed to search for emails. Retrying {i + 1}/{retries}...")
                      time.sleep(delay)
                      continue
                  
                  # If there are any matching emails, process the latest one
                  email_ids = messages[0].split()
                  if not email_ids:
                      logging.info(f"Failed to retrieve emails. Retrying {i + 1}/{retries}...")
                      time.sleep(delay)
                      continue
                  
                  latest_email_id = email_ids[-1]
                  status, msg_data = self.imap.fetch(latest_email_id, "(RFC822)")

                  # Iterate over the message data to retrieve the email content
                  for response_part in msg_data:
                      if isinstance(response_part, tuple):

                          # Parse the email content
                          msg = email.message_from_bytes(response_part[1])
                          subject, encoding = decode_header(msg["Subject"])[0]
                          if isinstance(subject, bytes):
                              subject = subject.decode(encoding or "utf-8")

                          # Extract the OTP code from the email subject
                          match = re.search(r"Expensify magic sign-in code: (\d+)", subject)
                          if match:
                              code = match.group(1)
                              return code

                  logging.info(f"No matching emails found. Retrying {i + 1}/{retries}...")
                  time.sleep(delay)
                      
              logging.warning("Max retries reached. OTP code not found.")
              return None

        def read_otp_from_email(email, password):
          with EmailHandler(email, password) as email_handler:
                email_handler.clean_inbox()  # Clean inbox
                otp = email_handler.read_otp_code()
          return otp

        async def complete_onboarding():
          await page.locator("text=Track and budget expenses").click()

          # Enter first name and last name
          await page.locator('input[name="fname"]').fill(FIRST_NAME)
          await page.locator('input[name="lname"]').fill(LAST_NAME)
          await page.get_by_role("button", name="Continue").last.click()

        async def sign_in_new_dot(page: Page, email: str, password: str):
          """
          Sign in into the new Expensify dot.
          """
          # Go to URL
          await page.goto(NEW_DOT_URL)
          
          # Enter email
          await page.get_by_test_id("username").fill(email)
          await page.get_by_role("button", name="Continue").click()

          try:
              # Await OTP
              
              await(expect(page.get_by_test_id("validateCode")).to_be_visible())
              await page.get_by_test_id("validateCode").fill('111111')
          except:
              # Else click the "Join" button
              await page.get_by_role("button", name="Join").click()

          try:
              await expect(page.get_by_text("What do you want to do today?")).to_be_visible()
              await complete_onboarding()
          except:
            pass

        async def test_app_returns_to_confirmation_page_when_tapping_back_button_on_category_page(page: Page):
            await page.get_by_label("Start chat (Floating action)").click()
            await page.get_by_label("Track expense").first.click()
            await page.get_by_role("button", name="Got it").click()
            await page.get_by_label("Manual").click()
            await page.get_by_placeholder("0").fill("1000")
            await page.locator("#numPadContainerView").get_by_role("button", name="Next").click()
            await page.get_by_role("button", name="Track expense").click()
            await page.get_by_role("button", name="Categorize it").first.click()
            await page.get_by_label("Back").click()
            # The 'Categorize' menu should not be open on the RHP after pressing 'back'
            await expect(page.get_by_test_id("IOURequestStepConfirmation").get_by_text("Categorize")).not_to_be_visible()

        await sign_in_new_dot(page, EXPENSIFY_EMAIL, EXPENSIFY_PASSWORD)
        await test_app_returns_to_confirmation_page_when_tapping_back_button_on_category_page(page)

        await browser.close()


def test_41783():
    asyncio.run(main())
