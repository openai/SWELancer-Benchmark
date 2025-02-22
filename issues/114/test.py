import re
import time
import email
import imaplib
from email.header import decode_header
from playwright.sync_api import sync_playwright, expect, Browser, Page
from playwright.sync_api._context_manager import PlaywrightContextManager


URL = 'https://dev.new.expensify.com:8082/'

IMAP_SERVER = "imap.gmail.com"
MAX_TRIES = 30


USER_EMAIL = "brianmunene69@gmail.com"
PASSWORD = "alqf ocav bnhj xupc" 

def get_magic_code(user_email=USER_EMAIL, password=PASSWORD, retries=5, delay=20):
    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    imap.login(user_email, password)

    for _ in range(retries):
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

                        match = re.search(r"Expensify magic sign-in code: (\d+)", subject)
                        if match:
                            code = match.group(1)
                            imap.logout()
                            return code
            else:
                print("No unread emails found with the subject. Retrying...")
        else:
            print("Failed to retrieve emails. Retrying...")
        time.sleep(delay)

    imap.logout()
    print("Max retries reached. Email not found.")
    return None

def login_user(p: PlaywrightContextManager, first_name="", last_name="") -> tuple[Browser, Page, str]:
    # Launch chromium and open new page
    browser = p.chromium.launch(
            channel="chrome",
            headless=False,
            args=[
                "--ignore-certificate-errors",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process"
            ],
            proxy={"server": "http://localhost:8080"},
            slow_mo=1000
        )
    page = browser.new_page()
    

    # Step 1: Open expensify url
    page.goto(URL)

    # Step 2: Enter email and click continue
    page.locator('input[type="email"]').fill(USER_EMAIL)
    page.locator('button[tabindex="0"]').click()

    # Step 3: Click join button
    try: 
        # page.locator('button[tabindex="0"]').click() 
        page.get_by_role("button", name="Join").click()
    except Exception:
        # otp = get_magic_code()
        otp = "123456"
        page.get_by_test_id("validateCode").fill(otp)

    # Wait for the page load to finish.
    page.wait_for_timeout(1000)

    if page.locator("text=What do you want to do today?").count() > 0:
        expect(page.locator("text=What do you want to do today?")).to_be_visible()
            
        # Step 4: Select 'Track and budget expenses' in onboarding page and click Continue
        page.locator("text='Track and budget expenses'").click()
        page.get_by_role("button", name="Continue").click()
        page.wait_for_timeout(1000)

        # Step 5: Enter first name, last name and click continue
        page.locator('input[name="fname"]').fill(first_name)
        page.locator('input[name="lname"]').fill(last_name)
        page.get_by_role("button", name="Continue").last.click()
        page.wait_for_timeout(1000)

    return browser, page


def test_table_row_caret_removed():
    with sync_playwright() as p:
        
        # Login as a user with an expired free trial
        browser, page = login_user(p, first_name="User", last_name="A")
        
        # Navigate to the settings.
        page.get_by_label("My settings").click()
        page.get_by_text("Subscription").click()

        # Check the RBR appears in the LHN in settings.
        expect(page.get_by_test_id("InitialSettingsPage").get_by_label("Subscription").locator("circle")).to_be_visible()

        page.close()
        browser.close()