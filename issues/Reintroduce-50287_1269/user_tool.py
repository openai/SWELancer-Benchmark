import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
import re, time
from PIL import Image
from io import BytesIO

import imaplib, pytest
import email
import random

# Expensify app URL
NEWDOT_URL = "https://dev.new.expensify.com:8082/"
OLDDOT_URL = "http://localhost:9000/"
EMAIL = "f2139887+50287@gmail.com"
PASSWORD = "sdib pdop ovyl uawy"


class IMAPOTPExtractor:
    def __init__(self, email_address, password):
        # Validate email and password input
        if not self._validate_email(email_address):
            raise ValueError("Invalid email address format.")
        self.original_email = email_address
        self.password = password

        # Generate new random email using "+" prefix
        random_suffix = random.randint(1000, 9999)
        current_timestamp = int(time.time())
        random_suffix = f"{current_timestamp}{random_suffix}"
        self.new_email = self._generate_new_email(email_address, random_suffix)

    def _validate_email(self, email_address):
        # Simple email validation
        return bool(re.match(r"[^@]+@[^@]+\.[^@]+", email_address))

    def _generate_new_email(self, email_address, suffix):
        # Add random number suffix to the email before the "@" symbol
        username, domain = email_address.split('@')
        return f"{username}+{suffix}@{domain}"

    def get_new_email(self):
        # Return the generated email with "+" suffix
        return self.new_email

    def set_new_email(self, email):
        self.new_email = email

    def check_for_otp(self):
        # Connect to the Gmail server using IMAP
        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(self.original_email, self.password)
            mail.select("inbox")

            # Fetch all unread emails
            status, messages = mail.search(None, "UNSEEN")
            if status != "OK":
                print("No unread emails found.")
                return None

            email_ids = messages[0].split()
            # Start from the latest email by reversing the list
            email_ids = email_ids[::-1]  # Reverse order to process latest first

            # Iterate over each email until OTP is found
            for email_id in email_ids:
                # Fetch the email by ID
                status, msg_data = mail.fetch(email_id, '(RFC822)')
                if status != "OK":
                    print("Error fetching email.")
                    continue

                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])

                        # Check if the To address matches the generated new email
                        if msg["To"] == self.new_email:
                            # Extract OTP from the email body
                            otp_code = self._extract_otp_from_email(msg)
                            if otp_code:
                                # Delete the email containing the OTP
                                mail.store(email_id, '+FLAGS', '\\Deleted')
                                mail.expunge()  # Permanently removes deleted emails from the mailbox

                                # Logout and return OTP
                                mail.close()
                                mail.logout()
                                return otp_code

            # Logout if OTP not found in unread emails
            mail.close()
            mail.logout()
            print("No OTP found in unread emails.")
            return None

        except imaplib.IMAP4.error:
            print("Failed to connect to Gmail. Please check your email address or password.")
            return None

    def _extract_otp_from_email(self, msg):
        # Extract OTP code from the email content
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
        # Find a 6-digit code in the email body
        match = re.search(r"\b\d{6}\b", text)
        return match.group(0) if match else None


gmail_account_helper = IMAPOTPExtractor(EMAIL, PASSWORD)


def generate_random_email():
    random_suffix = random.randint(1000, 9999)
    timestamp = int(time.time())
    return f"f2139887+{timestamp}{random_suffix}@gmail.com"


def old_dot_login(page, email, first_name="Test", last_name="User"):
    page.goto(OLDDOT_URL)
    page.locator("#qualifier-individual").check()
    page.locator("#login-main").fill(email)
    page.locator("#js_click_signUp_main").click()
    page.get_by_role("button", name="Join").click()
    page.locator("text=Track and budget expenses").click()
    page.get_by_role("textbox", name="First name").fill(first_name)
    page.get_by_role("textbox", name="Last name").fill(last_name)
    page.get_by_role("button", name="Continue").click()


def new_dot_login(page, email):
    page.goto(NEWDOT_URL)
    page.locator('input[type="email"]').fill(email)
    page.wait_for_timeout(2000)
    page.locator("div:nth-child(3) > div:nth-child(2) > div > div").first.click()
    # Wait for OTP
    page.wait_for_timeout(5000)
    gmail_account_helper.set_new_email(email)
    otp = gmail_account_helper.check_for_otp()
    try:
        page.get_by_test_id("validateCode").fill(otp)
    except:
        page.locator('input[data-testid="validateCode"]').fill("123456")
    try:
        page.get_by_role("button", name="Sign in").click()
    except Exception:
        pass

    page.get_by_text("Concierge").last.wait_for()


def create_sample_jpg():
    # Generates an image in memory and returns the bytes
    image = Image.new("RGB", (100, 100), color="blue")
    img_byte_arr = BytesIO()
    image.save(img_byte_arr, format="JPEG")
    img_byte_arr.seek(0)
    return img_byte_arr.getvalue()


def run_test(page, email_address):
    # change language to spanish
    rand_num = 99998
    page.get_by_label("My settings").click()
    page.get_by_text("Preferences").click()
    page.get_by_text("Language").click()
    page.get_by_label("Spanish").click()
    page.get_by_label("Recibidos").click()

    page.get_by_label("Iniciar chat (Acción flotante)").click()
    page.get_by_text("Iniciar chat").click()
    page.get_by_test_id("selection-list-text-input").click()
    page.get_by_test_id("selection-list-text-input").fill(f"f2139887+{rand_num}@gmail.com")
    page.get_by_label(f"f2139887+{rand_num}@gmail.com").last.click()
    page.get_by_label("Crear").last.click()
    page.get_by_text("Presentar gasto").click()

    with page.expect_file_chooser() as fc_info:
        page.get_by_label("Elegir archivo").click()
        file_chooser = fc_info.value
        file_chooser.set_files({
            "name": "input.jpg",
            "mimeType": "image/jpeg",
            "buffer": create_sample_jpg()
        })

    page.get_by_role("button", name="Presentar gasto").click()
    page.wait_for_timeout(5000)

    elements = page.locator('[aria-label="Ver detalles"]')  # or use get_by_label if supported in your version

    # Loop through the elements
    for i in range(elements.count()):
        element = elements.nth(i)

        # Check if the element contains the expected text
        if "Escaneado de recibo en proceso" in element.text_content().strip():
            element.click()
            print(f"Clicked element #{i + 1} because it contained the expected text.")
            break  # Exit the loop after the first match
    else:
        print("No matching element found with the expected text.")

    page.get_by_text("Importe • Efectivo").last.click()
    page.get_by_placeholder("0").fill("100")
    page.get_by_role("button", name="Guardar").click()
    page.wait_for_timeout(5000)
    if page.get_by_text("estableció el importe").last.is_visible():
        print("Test Passed")
    else:
        print("Test Failed")
        pytest.fail(f"AssertionError: Test Failed")


def test_expensify_50287():
    from utils.trace_cleaner import trace_cleaner
    with sync_playwright() as p:
        context_args = {}
        context_args["geolocation"] = {"latitude": 37.7749, "longitude": 122.4194}
        context_args["permissions"] = ["geolocation"]
        context_args["ignore_https_errors"] = True
        browser = p.chromium.launch(channel="chrome", headless=True,
                                    args=["--disable-web-security",
                                          "--disable-features=IsolateOrigins,site-per-process"])
        first_user_context = browser.new_context(**context_args)
        trace_path = "/app/expensify/user_tool/output_browser1.zip"
        first_user_context.tracing.start(screenshots=True, snapshots=True, sources=True)
        try:
            first_user_page = first_user_context.new_page()
            new_dot_login(first_user_page, EMAIL)
            run_test(first_user_page, EMAIL)
        except Exception as e:
            print("Test failed with error:", e)
            raise
        finally:
            first_user_context.tracing.stop()
            first_user_context.tracing.export(path=trace_path)
            trace_cleaner(trace_path)

        first_user_context.close()
        browser.close()
