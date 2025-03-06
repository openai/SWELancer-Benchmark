import sys, os
from utils.trace_cleaner import trace_cleaner

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
import time
import re
import random

NEWDOT_URL = "https://dev.new.expensify.com:8082/"
EMAIL = "dev091197@gmail.com"
task_id = 48694
EMAIL1 = f"dev091197+{task_id}@gmail.com"
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


def task_check(page):
    random_int_1 = 13
    random_int_2 = 21
    workspace_name =  f"WS-{random_int_1}{random_int_2}"
    room_name =  f"r-{random_int_1}{random_int_2}"
    email_1 = f"dev091197+{random_int_1}+{random_int_2}@gmail.com"
    test_name = "test inzi"
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
    page.wait_for_timeout(1000)
    page.get_by_label("Back").click()
    page.get_by_label("Inbox").click()
    page.wait_for_timeout(1000)
    page.get_by_label("Start chat (Floating action)").click()
    page.get_by_label("Start chat", exact=True).click()
    page.wait_for_timeout(1000)
    page.get_by_label("Room").first.click()
    page.get_by_placeholder("social").fill(room_name)
    page.wait_for_timeout(1000)
    page.get_by_test_id("WorkspaceNewRoomPage").get_by_label("WS-").get_by_text("Workspace").click()
    page.get_by_test_id("ValueSelectorModal").get_by_label(workspace_name).click()
    page.wait_for_timeout(1000)
    page.get_by_role("button", name="Create room").click()
    page.get_by_label(f"#{room_name}").click()
    page.wait_for_timeout(1000)
    page.get_by_test_id("ReportDetailsPage").get_by_label("Settings").click()
    page.get_by_text("Notify me about new messages").click()
    page.wait_for_timeout(1000)
    page.get_by_test_id("selection-list").get_by_label("Daily").click()
    page.get_by_test_id("ReportSettingsPage").get_by_label("Back").click()
    page.wait_for_timeout(1000)
    page.get_by_label("Leave").click()
    page.wait_for_timeout(1000)
    page.locator("#composer").last.click()
    page.locator("#composer").last.fill(f"message-{random_int_1}{random_int_2}")
    page.wait_for_timeout(1000)
    page.get_by_label("Send").last.click()
    page.get_by_label(f"#{room_name}").click()
    page.wait_for_timeout(1000)
    page.get_by_test_id("ReportDetailsPage").get_by_label("Settings").click()
    page.wait_for_timeout(2000)
    expect(page.get_by_text("Daily")).to_be_visible()


def test_expensify_0000():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=[
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
        ])
        
        first_user_context = browser.new_context(
            ignore_https_errors=True
        )
        
        # Start tracing with specified settings
        first_user_context.tracing.start(screenshots=True, snapshots=True, sources=True)
        
        page = first_user_context.new_page()
        page.wait_for_timeout(2000)
        
        try:
            new_dot_login(page, EMAIL1)
            page.wait_for_timeout(2000)
            task_check(page)
        finally:
            # Stop tracing and export the trace file
            first_user_context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            browser.close()


test_expensify_0000()