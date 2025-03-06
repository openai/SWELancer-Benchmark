import re
import time
from playwright.sync_api import sync_playwright
import random
import imaplib
import email as email_lib
from playwright.sync_api import sync_playwright, expect
import os
import requests
from PIL import Image, ImageDraw

NEWDOT_URL = "https://dev.new.expensify.com:8082/"

class IMAPOTPExtractor:
    def __init__(self, email_address, password):
        # Validate email and password input
        if not self._validate_email(email_address):
            raise ValueError("Invalid email address format.")
        self.original_email = email_address
        self.password = password

        # Generate new random email using "+" prefix
        # random_suffix = random.randint(1000, 9999)
        # current_timestamp = int(time.time())
        # random_suffix = f"{current_timestamp}{random_suffix}"
        random_suffix = "17400726985841"
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

    def set_new_email(self, email_address):
        self.new_email = email_address
    
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
                        msg = email_lib.message_from_bytes(response_part[1])

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


def launch_app(pw, headless=False, device=None, geolocation=None):
    browser = pw.chromium.launch(
        channel="chrome",
        headless=False,
        args=[
            "--ignore-certificate-errors",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ],
        proxy={"server": "http://localhost:8080"},
        slow_mo=2000
    )

    context_args = {}
    if device:
        context_args.update(pw.devices[device])
    if geolocation:
        context_args["geolocation"] = geolocation
        context_args["permissions"] = ["geolocation"]
    context = browser.new_context(**context_args)
    page = context.new_page()
    return browser, context, page


def login_and_initial_setup(page, email_extractor):
    page.goto(NEWDOT_URL)
    page.get_by_role("textbox", name="Phone or email").fill(email_extractor.get_new_email())

    continue_button = page.locator('button[tabindex="0"]')
    continue_button.click()
    
    try:
        page.locator('button[tabindex="0"]').click()
    except Exception:
        page.locator('button[tabindex="0"]').click()

    try:
        expect(page.get_by_text("want to do today")).to_be_visible(timeout=15000)
    except AssertionError:
        page.locator('button[tabindex="0"]').click()
    

    page.locator("text='Track and budget expenses'").wait_for(state="visible", timeout=10000)
    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()

    page.locator('input[name="fname"]').fill("TU")
    page.get_by_role("button", name="Continue").last.click()

    # Change the theme
    page.get_by_role("button", name="My settings").click()
    page.get_by_role("menuitem", name="Preferences").click()
    page.get_by_role("menuitem", name="Use device settings").click()
    page.get_by_role("button", name="Dark").click()
    page.get_by_role("button", name="Inbox").click()
    

def download_image(url, save_path):
    response = requests.get(url)
    if response.status_code == 200:
        with open(save_path, "wb") as file:
            file.write(response.content)
        print(f"Image downloaded successfully: {save_path}")
        return True
    else:
        print(f"Failed to download image. Status Code: {response.status_code}")
        return False

def check_background_change(image_path):
    img = Image.open(image_path).convert("RGBA")

    white_pixels = sum(1 for pixel in img.getdata() if pixel[:3] == (255, 255, 255))
    total_pixels = img.width * img.height
    white_percentage = (white_pixels / total_pixels) * 100

    return white_percentage > 5  

def send_the_image_file(page, img_path):
    page.get_by_text("TU").first.click()
    page.get_by_role("button", name="Create").last.click()

    add_attachment = page.get_by_test_id("PopoverMenuItem-Add attachment")
    with page.expect_file_chooser() as file_chooser_info:
        add_attachment.click()

    file_chooser = file_chooser_info.value
    file_chooser.set_files(img_path)
    page.get_by_role("dialog").get_by_role("button", name="Send").click()


def create_demo_image(filename="demo.png", size=(200, 200)):
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((50, 50, 150, 150), fill=(255, 0, 0, 255))  # Red color with full opacity
    
    image.save(filename, "PNG")
    return filename


def test_main():
    with sync_playwright() as pw:
        # User-provided email and password
        email_address = "rgarciatammy4@gmail.com"
        password = "ezkm eepd sctl nanx"

        # Initialize the IMAPOTPExtractor
        email_extractor = IMAPOTPExtractor(email_address, password)
        browser, context, page = launch_app(pw)
        login_and_initial_setup(page, email_extractor)

        upload_image_path = create_demo_image()
        send_the_image_file(page, upload_image_path)
        
        try:
            image_locator = page.locator("div[data-testid='comment'] img").nth(1)
        except:
            image_locator = page.locator("div[data-testid='comment'] img").first()

        image_url = image_locator.get_attribute("src")
        image_path = "downloaded_image.png"

        if image_url:
            if "blob:" not in image_url:
                if download_image(image_url, image_path):
                    check_background_change(image_path)
            else:
                image_data = image_locator.screenshot()
                with open(image_path, "wb") as file:
                    file.write(image_data)

                white_background_detected = check_background_change(image_path)
                assert white_background_detected == False, "Extra background color added, issue exists!"

        context.close()
        browser.close()