import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from utils.trace_cleaner import trace_cleaner

"""
Test to check if going 'back' from a 'not found' tax page
navigates to the WS editor page and not the WS selection page
"""

import pytest
from playwright.async_api import async_playwright, Page, expect
import time
import re
import imaplib
import email
import logging
from email.header import decode_header

# Load credentials
NEW_DOT_URL = "https://dev.new.expensify.com:8082"
EXPENSIFY_EMAIL = "testingq186+50465@gmail.com"
EXPENSIFY_PASSWORD = "kkfr hqiv yuxq rbso"
FIRST_NAME = "Testing"
LAST_NAME = "50465"

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
    otp = email_handler.read_otp_code()
    email_handler.clean_inbox()  # Clean inbox
    return otp

async def complete_onboarding(page):
  await page.locator("text=Track and budget expenses").click()

  # Enter first name and last name
  await page.locator('input[name="fname"]').fill(FIRST_NAME)
  await page.locator('input[name="lname"]').fill(LAST_NAME)
  await page.get_by_role("button", name="Continue").last.click()

async def login_if_not_logged_in(page: Page, email: str, password: str):
  """
  Sign in into the new Expensify dot.
  """
  # Go to URL
  await page.goto(NEW_DOT_URL)
  
  try:
    # If the user is already logged in, the inbox should be visible
    await expect(page.get_by_label("Inbox")).to_be_visible()
  except:
    try:
      # Enter email
      await expect(page.get_by_test_id("username")).to_be_visible()
      await page.get_by_test_id("username").fill(email)
      await page.get_by_role("button", name="Continue").click()
    except:
      pass

    try:
      # Await OTP
      await(expect(page.get_by_test_id("validateCode")).to_be_visible())
      await page.get_by_test_id("validateCode").fill('123456')
    except:
      # Else click the "Join" button
      await page.get_by_role("button", name="Join").click()

  try:
    await expect(page.get_by_text("What do you want to do today?")).to_be_visible()
    await complete_onboarding(page)
  except:
    pass

async def create_workspace(page: Page):
  await page.get_by_label("My settings").click()
  await page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()
  await page.get_by_role("button", name="New workspace").click()

async def toggle_taxes_in_workspace(page):
  await page.get_by_label("More features").click()
  await page.get_by_label("Document and reclaim eligible").click()

@pytest.mark.asyncio
async def test_disabling_tax_takes_to_ws_selection():
  async with async_playwright() as playwright:
    browser = await playwright.chromium.launch(headless=True, args=[
      '--disable-web-security',
      '--disable-features=IsolateOrigins,site-per-process',
    ])
    context = await browser.new_context(ignore_https_errors=True)
    # Start tracing
    await context.tracing.start(title="trace1", screenshots=True, snapshots=True, sources=True)

    try:
      page = await context.new_page()
      await login_if_not_logged_in(page, EXPENSIFY_EMAIL, EXPENSIFY_PASSWORD)
      await create_workspace(page)
      await toggle_taxes_in_workspace(page)
      await page.get_by_test_id("WorkspaceInitialPage").get_by_label("Taxes").click()
      page1 = await context.new_page()
      await page1.goto(page.url)
      await page1.bring_to_front()
      await page1.get_by_label("More features").click()
      await page1.get_by_label("Document and reclaim eligible").click()
      await page.bring_to_front()
      await page.get_by_test_id("NotFoundPage").get_by_label("Back").click()

      # Expect the Workspace Selection list to not be visible
      await expect(page.get_by_test_id("WorkspacesListPage").get_by_text("Workspaces")).not_to_be_visible()
      # Expect the Profile option to be visible (under Workspace Editor page)
      await expect(page.get_by_test_id("WorkspaceInitialPage").get_by_label("Profile")).to_be_visible()

    except Exception as e:
      # Reraise to ensure test fails, but still proceed to finally block
      raise e
    finally:
      # Stop tracing and save
      await context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
      # Clean the trace
      trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
      await browser.close()
