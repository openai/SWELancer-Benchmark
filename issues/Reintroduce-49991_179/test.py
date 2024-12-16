import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
import re
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page
import imaplib
import email
from email.header import decode_header

expensify_email = "totherandomuser+49821@gmail.com"
user_email = "totherandomuser@gmail.com"
password = "umei djwi bfmp jntm"
# user_email = "testerfreelancer555+50465@gmail.com"
# password = "snct ajbr yadx kwlq"



def mark_inbox_read(user_email, password):
    # Connect to the server
    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    imap.login(user_email, password)

    # Mark all existing unread emails as read in a single command
    imap.select("inbox")
    status, all_emails = imap.search(None, 'UNSEEN')
    if status == "OK" and all_emails[0]:
        email_ids = all_emails[0].replace(b' ', b',')
        imap.store(email_ids.decode(), '+FLAGS', '\\Seen')
    imap.logout()
    return


def get_magic_code(user_email, password, retries=5, delay=5):
    # Connect to the server
    return '123456'
    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    imap.login(user_email, password)

    # Retry logic for finding the magic code
    for attempt in range(retries):
        imap.select("inbox")
        status, messages = imap.search(None, '(UNSEEN SUBJECT "Expensify magic sign-in code:")')

        if status == "OK":
            email_ids = messages[0].split()

            if email_ids:
                latest_email_id = email_ids[-1]
                status, msg_data = imap.fetch(latest_email_id, "(RFC822)")

                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        subject, encoding = decode_header(msg["Subject"])[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding or "utf-8")

                        # Search for the magic code in the subject
                        match = re.search(r"Expensify magic sign-in code: (\d+)", subject)
                        if match:
                            code = match.group(1)
                            imap.logout()
                            return code
            else:
                print("No unread emails found with the subject. Retrying...")
        else:
            print("Failed to retrieve emails. Retrying...")

        # Wait for the specified delay before trying again
        time.sleep(delay)

    imap.logout()
    print("Max retries reached. Email not found.")
    return None


def login(p, context):
    page = context.new_page()
    page.goto('https://dev.new.expensify.com:8082')

    # step 0: Mark inbox read
    mark_inbox_read(user_email, password)

    # Step 1: Enter username and continue
    page.get_by_test_id("username").click()
    page.get_by_test_id("username").fill(expensify_email)
    page.get_by_role("button", name="Continue").click()

    # Step 2: Mark Inbox read and then get magic code from email
    magic_code = get_magic_code(user_email, password, retries=3, delay=10)

    # Step 3: Fill in the magic code
    validate_code_input = page.locator('input[name="validateCode"]')
    expect(validate_code_input).to_be_visible()
    validate_code_input.fill(magic_code)
    page.wait_for_timeout(1000)

    return page





# Utility function to generate a unique random email based on the current timestamp
def generate_random_email():
    timestamp = int(time.time())
    return f"freelanceapptest+{timestamp}@gmail.com"

# Function to log in a user and complete initial onboarding steps
def login_user(p: PlaywrightContextManager, first_name="Milan", last_name="T") -> tuple[Browser, Page, str]:
    # Launch Chromium browser in non-headless mode for testing
    device = p.devices["Pixel 7"]
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(**device, ignore_https_errors=True)
    page = context.new_page()
    user_email = generate_random_email() 

    # Step 1: Navigate to the Expensify development environment login page
    page.goto('https://dev.new.expensify.com:8082/')
    page.wait_for_timeout(2000)  

    # Step 2: Enter the generated email address and proceed to the next step
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(5000)  

    # Step 3: Attempt to click "Join" button if present; continue if not found
    try: 
        page.locator('button[tabindex="0"]').click() 
        page.wait_for_timeout(5000)
    except Exception:
        pass  

    # Step 4: Confirm dashboard arrival by checking for welcome text visibility
    expect(page.locator("text=What do you want to do today?")).to_be_visible()

    # Step 5: Select "Track and budget expenses" option on onboarding and proceed
    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()
    page.wait_for_timeout(1000)

    # Step 6: Enter first and last names and continue
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()
    page.wait_for_timeout(1000)

    return browser, page, user_email 

# Test to verify that the back button navigates the user to the LHN after deleting a task. 
def test_back_button():
    with sync_playwright() as p:
        # Step 1: Log in a user and complete onboarding
        # browser, page, user_email = login_user(p)
        # Step 1: Main Browser Login
        browser = p.chromium.launch(headless=True, args = [
        "--disable-web-security",
        "--disable-features=IsolateOrigins, site-per-process"
        ], slow_mo=1000)   
        context = browser.new_context()
        page = login(p, context)


        # Step 2: Create a group chat
        # page.get_by_label("Back").click()
        # page.get_by_label("Close").click()
        page.get_by_label("Start chat (Floating action)").click()
        page.get_by_text("Start chat").click()
        page.get_by_test_id("selection-list-text-input").fill("testuser@gmail.com")
        page.wait_for_timeout(1000)
        page.get_by_role("button", name="Add to group").click()
        page.get_by_test_id("selection-list-text-input").fill("test@gmail.com")
        page.wait_for_timeout(1000)
        page.get_by_role("button", name="Add to group").click()
        page.get_by_role("button", name="Next").click()
        page.get_by_role("button", name="Start group").click()

        # Step 3: Assign A task and Delete it
        page.get_by_label("Create").click()
        page.get_by_text("Assign task").click()
        page.get_by_role("textbox", name="Title").fill("Test 1")
        page.get_by_role("button", name="Next").click()
        page.get_by_role("button", name="Confirm task").click()
        page.wait_for_timeout(1000)
        page.get_by_label("Create").click()
        page.get_by_text("Assign task").click()
        page.get_by_role("textbox", name="Title").fill("Test 2")
        page.get_by_role("button", name="Next").click()
        page.get_by_role("button", name="Confirm task").click()
        page.wait_for_timeout(1000)
        page.locator("div").filter(has_text=re.compile(r"^Test 1$")).nth(1).click()
        page.get_by_role("button", name="Test").click()
        page.wait_for_timeout(2000)
        page.set_viewport_size({'width': 375, 'height': 812}) 

        # page.locator("div:nth-child(5) > div > div > div > div > div > div > div > div:nth-child(2) > .css-view-175oi2r").click()
        page.get_by_label("Delete").click()
        # page.pause()


        page.get_by_role("button", name="Delete").click()
        page.wait_for_timeout(6000)
        
        # Step 5: Press back and verify tou have been navigated to LHN
        back_btn = page.locator('button[aria-label="Back"]').last
        expect(back_btn).to_be_visible()
        back_btn.click()
        page.wait_for_timeout(1000)
        # page.get_by_label("Back")

        expect(page.get_by_test_id("comment").get_by_text("[Deleted task]")).not_to_be_visible()

            
        #-----------------
        browser.close()


