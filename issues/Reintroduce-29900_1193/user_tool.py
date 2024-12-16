import sys, os

from utils.trace_cleaner import trace_cleaner

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
import re
from playwright.sync_api import Playwright, sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page
import imaplib
import email
from email.header import decode_header
from datetime import datetime, timezone

EMAIL_USERNAME = "aliceoglualice@gmail.com"
EMAIL_PASSWORD = "cfpy ofxm lcmq aeta"
# Email username postfix
EMAIL_USERNAME_POSTFIX = "29900.178212611614"

# Function to fetch the magic code from email
def get_magic_code(user_email, password, since=None, retries=5, delay=10):
    # Step 1: Initialize email fetching parameters
    if since is None:
        since = datetime.now(timezone.utc).replace(second=0, microsecond=0)

    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    
    # Step 2: Login to the email account
    imap.login(user_email, password)

    for _ in range(retries):
        # Step 3: Select the inbox and search for unread magic code emails
        imap.select("inbox")
        status, messages = imap.search(None, '(UNSEEN SUBJECT "Expensify magic sign-in code:")')

        if status == "OK":
            email_ids = messages[0].split()

            if email_ids:
                # Step 4: Fetch the latest email
                latest_email_id = email_ids[-1]
                status, msg_data = imap.fetch(latest_email_id, "(RFC822)")

                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        # Step 5: Parse email content and look for the magic code
                        msg = email.message_from_bytes(response_part[1])
                        subject, encoding = decode_header(msg["Subject"])[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding or "utf-8")

                        match = re.search(r"Expensify magic sign-in code: (\d+)", subject)
                        email_date = email.utils.parsedate_to_datetime(msg["Date"])
                        if match and email_date >= since:
                            # Step 6: Return the extracted magic code
                            code = match.group(1)
                            imap.logout()
                            return code
                print("Email doesn't match conditions. Retrying...")
            else:
                print("No unread emails found with the subject. Retrying...")
        else:
            print("Failed to retrieve emails. Retrying...")
        time.sleep(delay)

    # Step 7: Logout from IMAP and return None after max retries
    imap.logout()
    print("Max retries reached. Email not found.")
    return None


def generate_user_email(user_id):
    """
    Generate an email address for a user login.
    """
    temp = EMAIL_USERNAME.rsplit("@", 1)
    username = temp[0].strip()
    domain = temp[1].strip()
    return f"{username}+{EMAIL_USERNAME_POSTFIX}{user_id}@{domain}"


def login_user(p: PlaywrightContextManager, first_name, last_name, user_id) -> tuple[Browser, PlaywrightContextManager, Page, str]:
    # Launch the browser with ignore HTTPS errors option
    browser = p.chromium.launch(headless=True, args=[
        "--disable-web-security",
        "--disable-features=IsolateOrigins,site-per-process",
        "--ignore-certificate-errors"
    ])
    context = browser.new_context(ignore_https_errors=True)
    # Start tracing right away
    context.tracing.start(screenshots=True, snapshots=True, sources=True)
    page = context.new_page()
    user_email = generate_user_email(user_id)

    # Step 1: Open expensify url
    page.goto('https://dev.new.expensify.com:8082/')

    # Step 2: Enter email and click continue
    page.get_by_test_id("username").fill(user_email)
    page.get_by_role("button", name="Continue").click()
    # Check if OTP is required for the login
    try:
        expect(page.get_by_test_id("SignInPage").get_by_test_id("validateCode")).to_be_visible(timeout=5000)
    except (AssertionError, TimeoutError):
        # If not required, expect the join button to appear and click the button
        page.get_by_test_id("SignInPage").get_by_role("button", name="Join").click()
    else:
        # Get the OTP and complete verification
        otp_code = get_magic_code(EMAIL_USERNAME, EMAIL_PASSWORD)
        page.get_by_test_id("SignInPage").get_by_test_id("validateCode").fill(otp_code)
        try:
            page.get_by_test_id("SignInPage").get_by_role("button", name="Sign in").click(timeout=2000)
        except (AssertionError, TimeoutError):
            pass

    # Check if onboarding is required
    try:
        expect(page.get_by_text("What do you want to do today?")).to_be_visible(timeout=5000)
    except (AssertionError, TimeoutError):
        pass
    else:
        # Complete the onboarding
        page.get_by_label("Track and budget expenses").click()
        page.get_by_role("textbox", name="First name").fill(first_name)
        page.get_by_role("textbox", name="Last name").fill(last_name)
        page.get_by_role("button", name="Continue").click()
    
    return browser, context, page, user_email


def test_invite_member_name_visibility_on_hover():
    with sync_playwright() as p:
        #-----------------------------------------------
        # Step 1: Login user2 with trace
        #-----------------------------------------------
        browser2 = None
        context2 = None
        page2 = None
        user_email2 = None
        try:
            browser2, context2, page2, user_email2 = login_user(p, "Bob", "B", 2)
        except Exception as e:
            print(f"Error logging in user2: {e}")
        finally:
            # Stop and export trace for user2
            if context2:
                try:
                    context2.tracing.stop()
                    context2.tracing.export_to_file("/app/expensify/user_tool/output_browser1.zip")
                    trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
                except Exception as trace_err:
                    print(f"Error exporting user2 trace: {trace_err}")
            if browser2:
                browser2.close()

        #-----------------------------------------------
        # Step 2: Login user1 and run test steps
        #-----------------------------------------------
        browser = None
        context = None
        page = None
        user_email = None
        try:
            browser, context, page, user_email = login_user(p, "Alice", "A", 1)

            # Step 3: Search user2 to send message
            page.get_by_label("Start chat (Floating action)").click()
            page.get_by_text("Start chat").click()
            page.get_by_test_id("selection-list-text-input").fill(user_email2)
            page.wait_for_timeout(1000)
            # Step 4: Send message to User2
            page.locator(f'div[dir="auto"]:has-text("{user_email2}")').last.click()
            page.get_by_role("textbox").fill("Hello")
            page.get_by_label("Start chat (Floating action)").click()

            # Step 5: Create new workspace
            page.get_by_text("New workspace").click()
            page.get_by_text("Members").click()
            page.wait_for_timeout(1000)

            # Step 6: Invite User2
            page.get_by_role("button", name="Invite member").click()
            page.locator('input[data-testid="selection-list-text-input"]').fill(user_email2)
            page.locator(f'div[dir="auto"]:has-text("{user_email2}")').last.click()
            next_button = page.get_by_role("button", name="Next")
            next_button.click()
            page.get_by_test_id("WorkspaceInviteMessagePage").get_by_role("button", name="Invite").click()

            page.wait_for_timeout(1000)

            # Step 7: Hover over avatars
            avatar_count = page.locator('[data-testid="SvgFallbackAvatar Icon"]').count()
            for i in range(0, avatar_count):
                avatar = page.locator('[data-testid="SvgFallbackAvatar Icon"]').nth(i)
                if avatar.is_visible() and avatar.is_enabled():
                    try:
                        avatar.hover(timeout=500)
                        print(f"Hovered over avatar {i}")
                    except Exception as e:
                        print(f"Failed to hover over avatar {i}: {e}")
                 
                page.wait_for_timeout(100)

            # Step 8: Locate the hover container with "Bob B" and assert its visibility
            hover_container = page.locator('div.css-text-146c3p1:has-text("Bob B")').nth(3)
            hover_container.wait_for(timeout=3000)

            # Step 9: Assert "Bob B" exists and is visible
            assert hover_container.is_visible(), "Hover element containing 'Bob B' is not visible"

        except Exception as e:
            print(f"Error during user1 steps or final assertion: {e}")
            raise e
        finally:
            # Stop and export trace for user1
            if context:
                try:
                    context.tracing.stop()
                    context.tracing.export_to_file("/app/expensify/user_tool/output_browser2.zip")
                    trace_cleaner("/app/expensify/user_tool/output_browser2.zip")
                except Exception as trace_err:
                    print(f"Error exporting user1 trace: {trace_err}")
            if browser:
                browser.close()
