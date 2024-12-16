import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
import re, time
import imaplib 
import email
import re
import random
from PIL import Image
from io import BytesIO
from playwright.sync_api import expect

from utils.trace_cleaner import trace_cleaner

NEWDOT_URL = "https://dev.new.expensify.com:8082/"
OLDDOT_URL = "http://localhost:9000/" 
EMAIL = "randomturing@gmail.com"
PASSWORD = "ryfo zezf tmlq xybs"

static_email = "randomturing+40121564@gmail.com"

def generate_random_email():
    random_suffix = random.randint(1000, 9999)
    timestamp = int(time.time())
    email_prefix = EMAIL.split("@")[0]
    return f"{email_prefix}+{timestamp}{random_suffix}@gmail.com"
 
    
def new_dot_login_join(page, email):
    page.goto(NEWDOT_URL)
    page.locator('input[type="email"]').fill(email)
    page.wait_for_timeout(2000)
    page.get_by_role("button", name="Continue").click()
    page.get_by_role("button", name="Join").click()


def test_expensify_50064():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"])
        first_user_context = browser.new_context(ignore_https_errors=True)
        # Start the trace
        first_user_context.tracing.start(screenshots=True, snapshots=True, sources=True)
        
        try:
            first_user_page = first_user_context.new_page()
            first_user_email = static_email
            new_dot_login_join(first_user_page, first_user_email)
            first_user_page.wait_for_timeout(2000)
            first_user_page.locator("text=Track and budget expenses").wait_for()

            new_page = first_user_context.new_page()

            new_page.goto(NEWDOT_URL)
            first_user_page.close()
            new_page.click("div[aria-label='Track and budget expenses']")
            # Adding this because the "What's your name?" selector shows for a split second
            new_page.wait_for_timeout(2000) 
            locator = new_page.get_by_text("What's your name?")
            expect(locator).to_be_visible()
        finally:
            # Stop tracing and clean the trace
            first_user_context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
