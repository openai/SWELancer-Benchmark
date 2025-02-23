import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import re
import time
import email
import pytest
import random
import imaplib
from playwright._impl._page import Page
from playwright.sync_api import sync_playwright, expect


BASE_EMAIL = "brianmuneneturing+20569@gmail.com"
PASSWORD = "zukqdnszutrrlhhl"


class EmailHandler:
    def __init__(self, email_address, password):

        if not self._validate_email(email_address):
            raise ValueError("Invalid email address format.")
        self.original_email = email_address
        self.password = password


        random_suffix = random.randint(1000, 9999)
        current_timestamp = int(time.time())
        random_suffix = f"{current_timestamp}{random_suffix}"
        self.new_email = self._generate_new_email(email_address, random_suffix)

    def _validate_email(self, email_address):

        return bool(re.match(r"[^@]+@[^@]+\.[^@]+", email_address))

    def _generate_new_email(self, email_address, suffix):

        username, domain = "testerfreelancer@gmail.com".split('@')
        return f"{username}+{suffix}@{domain}"

    def get_new_email_address(self):

        return self.new_email

    def get_email_address(self):

        return self.original_email

    def check_for_otp(self, page, target=False):

        if not target:
            target = self.original_email
        try:
            tries = 1
            limit_tries = 5
            while tries <= limit_tries:
                mail = imaplib.IMAP4_SSL("imap.gmail.com")
                mail.login(self.original_email, self.password)
                mail.select("inbox")


                status, messages = mail.search(None, "UNSEEN")
                if status != "OK":
                    print("No unread emails found.")

                email_ids = messages[0].split()

                email_ids = email_ids[::-1]  # Reverse order to process latest first


                for email_id in email_ids:

                    status, msg_data = mail.fetch(email_id, '(RFC822)')
                    if status != "OK":
                        print("Error fetching email.")
                        continue

                    for response_part in msg_data:
                        if isinstance(response_part, tuple):
                            msg = email.message_from_bytes(response_part[1])


                            if msg["To"] == target:

                                otp_code = self._extract_otp_from_email(msg)
                                if otp_code:

                                    mail.store(email_id, '+FLAGS', '\\Deleted')
                                    mail.expunge()  # Permanently removes deleted emails from the mailbox


                                    mail.close()
                                    mail.logout()
                                    return otp_code
                tries += 1
                page.wait_for_timeout(1000)


            mail.close()
            mail.logout()
            print("No OTP found in unread emails.")
            return None

        except imaplib.IMAP4.error as error:
            print(error)
            print("Failed to connect to Gmail. Please check your email address or password.")
            return None

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

    def clear_inbox(self):
        """
        Delete all existing messages from the Inbox.
        """
        print("Deleting all existing messages from the email inbox")
        with imaplib.IMAP4_SSL(host="imap.gmail.com") as imap:
            imap.login(self.original_email, self.password)
            imap.select("inbox")
            imap.store("1:*", "+FLAGS", "\\Deleted")
            imap.expunge()
            imap.close()


@pytest.fixture
def setup_playwright():

    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(
        channel="chrome",
        headless=True,
        args=[
            "--ignore-certificate-errors",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ],
        proxy={"server": "http://localhost:8080"},
        slow_mo=1000
    )
    context = browser.new_context()
    yield context  # Yield the page object to the test function
    browser.close()
    playwright.stop()



def login_user(page: Page, account: EmailHandler):


    page.goto("https://dev.new.expensify.com:8082/")

    page.locator('input[type="email"]').fill(BASE_EMAIL)
    page.locator('button[tabindex="0"]').click()

    try:
        expect(page.get_by_role("button", name="Sign in")).to_be_visible()

        otp = "203569"
        page.get_by_test_id("validateCode").fill(otp)
    except Exception as error:
        print(error)
        page.get_by_role("button", name="Join").click()


@pytest.mark.parametrize("first_name, last_name", [("Test", "User")])
def test_selected_highlight(setup_playwright, first_name, last_name):
    context = setup_playwright
    account = EmailHandler(email_address=BASE_EMAIL, password=PASSWORD)
    user_email = account.get_email_address()


    page = context.new_page()
    login_user(page, account)


    page.get_by_label("My settings").click()

    page.get_by_text("Address").click()

    page.get_by_text("Country").click()
    page.get_by_test_id("selection-list-text-input").fill("as")
    page.get_by_label("Ascension Island").click()

    page.get_by_role("textbox", name="Zip / Postcode").fill("ascn 1zz")
    page.get_by_role("textbox", name="Zip / Postcode").press("Enter")

    expect(page.get_by_text("Incorrect zip code format.")).not_to_be_visible()

