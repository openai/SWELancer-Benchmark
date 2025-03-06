import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
import time
import re
import random

NEWDOT_URL = "https://dev.new.expensify.com:8082/"
task_id = 49786
EMAIL = f"dev091197+{task_id}@gmail.com"
PASSWORD = ""


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


def category_approvers(page):
    random_int_1 = 23
    random_int_2 = 241
    workspace_name =  f"WS-{random_int_1}{random_int_2}"
    page.get_by_label("My settings").click()
    page.wait_for_timeout(2000)
    page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()
    page.get_by_role("button", name="New workspace").first.click()
    page.wait_for_timeout(1000)
    page.get_by_test_id("WorkspacePageWithSections").get_by_text("Name").click()
    page.wait_for_timeout(1000)
    page.get_by_role("textbox", name="Name").press("ControlOrMeta+a")
    page.wait_for_timeout(1000)
    page.get_by_role("textbox", name="Name").fill(workspace_name)
    page.wait_for_timeout(1000)
    page.get_by_role("button", name="Save").click()


    page.get_by_label("More features").click()
    page.get_by_label("Configure how spend is").click()


    page.get_by_test_id("WorkspaceInitialPage").get_by_label(
        "Profile"
    ).click()
    page.get_by_test_id("WorkspacePageWithSections").get_by_text(
        "Default currency"
    ).click()
    page.get_by_test_id("selection-list-text-input").fill("usd")
    page.get_by_label("USD - $").click()


    routing_number = "011401533"
    account_number = "1111222233334444"
    page.get_by_label("Workflows").click()
    page.get_by_label("Connect bank account").click()
    page.get_by_label("Connect manually").click()
    page.get_by_role("textbox", name="Routing number").fill(routing_number)
    page.get_by_role("textbox", name="Account number").fill(account_number)
    page.get_by_role("button", name="Next").click()
    page.get_by_test_id("PersonalInfo").get_by_label("Back").click()
    page.wait_for_timeout(2000)

    expect(
        page.get_by_role("textbox", name="Routing number")
    ).to_be_disabled()
    expect(
        page.get_by_role("textbox", name="Account number")
    ).to_be_disabled()


def test_run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=[
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
        ])
        page = browser.new_page()


        page.goto('https://dev.new.expensify.com:8082/', timeout=60000)

        new_dot_login(page, EMAIL)
        
        category_approvers(page)

        browser.close()