import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)


import time
import os
import imaplib
import email
import re
from email.header import decode_header
from playwright.sync_api import sync_playwright, expect
import io
import os


expensify_email = "testuserexpensify1+48697@gmail.com"
user_email = "testuserexpensify1@gmail.com"
password = "aedyeaocujbrrcal"


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
    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    imap.login(user_email, password)

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
                        subject_header = msg["Subject"]
                        if subject_header is not None:
                            subject, encoding = decode_header(subject_header)[0]
                            if isinstance(subject, bytes):
                                subject = subject.decode(encoding or "utf-8")

                            match = re.search(r"Expensify magic sign-in code: (\d+)", subject)
                            if match:
                                code = match.group(1)
                                imap.logout()
                                return code
                        else:
                            print("Email does not have a subject header. Retrying...")
            else:
                print("No unread emails found with the subject. Retrying...")
        else:
            print("Failed to retrieve emails. Retrying...")

        time.sleep(delay)

    imap.logout()
    print("Max retries reached. Email not found.")
    return None


def login_user1(p, first_name="Pratik", last_name="Test") -> tuple:
    
    browser = p.chromium.launch(headless=True, args=[
        "--disable-web-security",
        "--disable-features=IsolateOrigins,site-per-process"
    ])
    iphone_11 = p.devices['iPhone 11']
    context = browser.new_context(**iphone_11)
    page = context.new_page()

    page.goto('https://dev.new.expensify.com:8082/') 

    # step 0: Mark inbox read
    mark_inbox_read(user_email, password)
    
    # Step 1: Enter username and continue
    page.get_by_test_id("username").click()
    page.get_by_test_id("username").fill(expensify_email)
    page.get_by_role("button", name="Continue").click()
    
    try: 
        page.locator('button[tabindex="0"]').click() 
    except Exception:
        pass
    try: 
        page.locator('button[tabindex="0"]').click() 
    except Exception:
        pass

    try:
        # Step 2: Mark Inbox read and then get magic code from email
        magic_code = "756400"
        # Step 3: Fill in the magic code
        validate_code_input = page.locator('input[name="validateCode"]')
        expect(validate_code_input).to_be_visible()
        validate_code_input.fill(magic_code)
        page.wait_for_timeout(1000)
    except:
        pass

    return browser, page, user_email


def chat_attachment_upload(page, filename="test_file.txt"):
   
    page.locator('button[aria-label="Navigates to a chat"]').last.click()
    page.wait_for_timeout(1000)
    page.wait_for_timeout(1000)
    page.get_by_label("Create").click()
    edit_photo_button = page.locator('div[aria-label="Add attachment"]').locator("visible=true")
    

    with page.expect_file_chooser() as file_chooser_info:
        edit_photo_button.click()
    page.wait_for_timeout(3000)
    file_chooser = file_chooser_info.value
    file_path = os.path.join(os.getcwd(), filename)
    file_chooser.set_files(file_path)
    print(f"Uploading file: {file_path}")


    uploaded_file_button = page.locator('button[aria-label="test_file.txt"]')
    while uploaded_file_button.count() == 0:
        page.wait_for_timeout(1000)
    print("File uploaded successfully.")

    save_button = page.locator('button:has-text("Send")')
    save_button.click()
    page.wait_for_timeout(200)

    assert is_ui_stable(page, filename) == True, "Screen blink detected. The UI changed significantly."



def is_ui_stable(page, filename, check_duration=5, interval=0.01):
    """Check if the UI is stable by monitoring the presence of the uploaded file's name."""
    initial_count = page.locator(f'div[data-testid="report-actions-list"] >> text={filename}').count()

    # Monitor the element count for `check_duration` seconds
    end_time = time.time() + check_duration
    while time.time() < end_time:
        current_count = page.locator(f'div[data-testid="report-actions-list"] >> text={filename}').count()
        if current_count != initial_count:
            # If the count changes, the UI is not stable
            return False
        time.sleep(interval)
    
    # If the count remains the same, the UI is stable
    return True


def create_file(file_path):
    with open(file_path, "w") as file:
        file.write("This is a sample line of text.\n" * 50)


def test_run(member_first_name="Pratik", member_last_name="Test"):

    current_directory = os.getcwd()
    file_name = "test_file.txt"
    file_path = os.path.join(current_directory, file_name)
    create_file(file_path)

    with sync_playwright() as p:
        browser_member, page_member, user_email1 = login_user1(p, member_first_name, member_last_name)  
        chat_attachment_upload(page_member)

        os.remove(file_path)    
        browser_member.close()
