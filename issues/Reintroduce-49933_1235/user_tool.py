import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
import time
import re
import random

from utils.trace_cleaner import trace_cleaner

NEWDOT_URL = "https://dev.new.expensify.com:8082/"
EMAIL = "dev091197@gmail.com"
LOGIN_EMAIL = "dev091197+005@gmail.com"
PASSWORD = "ptul fwbd fvze yzva"

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
    default_otp_code = "123456"
    return default_otp_code
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
  page.wait_for_timeout(2000)
  page.get_by_role("button", name="Continue").nth(0).click()
  page.wait_for_timeout(10000)
  gmail_account_helper.set_new_email(email)
  otp = gmail_account_helper.check_for_otp()
  page.locator('input[data-testid="validateCode"]').fill(otp)
  try:
    page.get_by_role("button", name="Sign In").click()
  except:
    pass

def task_check(page):
  page.get_by_label("Start chat (Floating action)").click()
  page.get_by_label("Start chat", exact=True).click()
  page.get_by_test_id("selection-list-text-input").fill("test_user_not_to_remove_1@gmail.com")
  page.wait_for_timeout(1000)
  page.get_by_role("button", name="Add to group").click()
  page.get_by_test_id("selection-list-text-input").fill("test_user_to_remove_1@gmail.com")
  page.wait_for_timeout(1000)
  page.get_by_role("button", name="Add to group").click()
  page.wait_for_timeout(1000)
  page.get_by_role("button", name="Next").click()
  page.get_by_role("button", name="Start group").click()
  page.wait_for_timeout(1000)
  page.locator("div:nth-child(3) > div:nth-child(2) > div:nth-child(2) > div > div > div > div > div > div > div > div > div > div > div > div").first.click()
  page.get_by_label("Members").click()
  page.wait_for_timeout(1000)
  page.locator("div:nth-child(4) > div > div:nth-child(2) > div > div:nth-child(4) > div > div > div").click()
  page.get_by_role("button", name="Remove from group").click()
  page.get_by_role("button", name="Remove", exact=True).click()
  page.wait_for_timeout(2000)
  page.get_by_test_id("ReportParticipantsPage").get_by_label("Back").click()
  page.locator("div").filter(has_text=re.compile(r"^Details$")).nth(1).click()
  page.get_by_label("Back").click()
  page.wait_for_timeout(2000)
  expect(page.get_by_label("Chat welcome message").last).not_to_contain_text("test_user_to_remove_1@gmail.com")

def test_expensify_0000():
   with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=[
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
        ])

    first_user_context = browser.new_context(
      ignore_https_errors=True
    )

    # Start tracing
    first_user_context.tracing.start(screenshots=True, snapshots=True, sources=True)

    page = first_user_context.new_page()
    page.wait_for_timeout(2000)

    try:
      new_dot_login(page, LOGIN_EMAIL)
      page.wait_for_timeout(2000)
      task_check(page)
    except:
      # We catch any exception so that the trace is still saved.
      pass
    finally:
      # Stop tracing and save
      first_user_context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
      trace_cleaner("/app/expensify/user_tool/output_browser1.zip")

    browser.close()