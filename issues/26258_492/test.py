import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import re
import time
from playwright.sync_api import sync_playwright
import random
import imaplib
import email as email_lib
from playwright.sync_api import sync_playwright, expect
import os


NEWDOT_URL = "https://dev.new.expensify.com:8082/"

class IMAPOTPExtractor:
    def __init__(self, email_address, password):

        if not self._validate_email(email_address):
            raise ValueError("Invalid email address format.")
        self.original_email = email_address
        self.password = password


        random_suffix = random.randint(1000, 9999)
        random_suffix_2 = random_suffix + 1

        current_timestamp = int(time.time())
        random_suffix = f"565439872"
        random_suffix_2 = f"6552447256"

        self.new_email_1 = self._generate_new_email(email_address, random_suffix)
        self.new_email_2 = self._generate_new_email(email_address, random_suffix_2)
    
    def _validate_email(self, email_address):

        return bool(re.match(r"[^@]+@[^@]+\.[^@]+", email_address))
    
    def _generate_new_email(self, email_address, suffix):

        username, domain = email_address.split('@')
        return f"{username}+{suffix}@{domain}"

    def get_new_email_1(self):

        return self.new_email_1
    
    def get_new_email_2(self):

        return self.new_email_2
    
    def check_for_otp(self, email):
       return "123456"


def create_simple_pdf(filename="sample.pdf"):
    """
    Creates a simple PDF file in the current working directory without using any external libraries.
    
    Args:
    - filename (str): The name of the PDF file to be created.
    
    Returns:
    - str: The absolute path of the created PDF file.
    """
    pdf_content = """%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << >> >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT
/F1 24 Tf
100 700 Td
(Hello, this is a simple PDF file) Tj
ET
endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 6
0000000000 65535 f 
0000000010 00000 n 
0000000079 00000 n 
0000000178 00000 n 
0000000328 00000 n 
0000000407 00000 n 
trailer
<< /Size 6 /Root 1 0 R >>
startxref
488
%%EOF
"""


    with open(filename, "wb") as file:
        file.write(pdf_content.encode('latin1'))  # PDF requires Latin-1 encoding
    
    return filename


def delete_pdf(filename="sample.pdf"):
    """
    Deletes a PDF file in the current working directory.
    
    Args:
    - filename (str): The name of the PDF file to be deleted.
    
    Returns:
    - bool: True if the file was successfully deleted, False if the file does not exist.
    """
    file_path = os.path.join(os.getcwd(), filename)
    
    if os.path.exists(file_path):
        os.remove(file_path)
        return True
    else:
        print(f"File not found, could not delete: {file_path}")
        return False


def click_until_visible(page, button_selector: str, desired_selector: str, max_retries: int = 10, timeout: int = 30):
    """
    Clicks a button until the desired element becomes visible or max retries are reached.

    :param page: Playwright Page instance.
    :param button_selector: Selector for the button to click.
    :param desired_selector: Selector for the element to wait for.
    :param max_retries: Maximum number of clicks to attempt.
    :param timeout: Maximum time to wait for the desired element to become visible.

    :return: Locator for the desired element.
    """
    timeout = timeout * 1000  # Convert seconds to milliseconds
    retries = 0
    while retries < max_retries:

        page.locator(button_selector).click(timeout=timeout)
        
        try:

            locator = page.locator(desired_selector).wait_for(state="visible", timeout=timeout)
            return locator
        except Exception:

            retries += 1


    raise Exception(f"Desired element '{desired_selector}' not found after {max_retries} clicks.")


def launch_app(pw, headless=True, device=None, geolocation=None):
    browser = pw.chromium.launch(
            channel="chrome",
            headless=True,
            args=[
                "--ignore-certificate-errors",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process"
            ],
            proxy={"server": "http://localhost:8080"},
            slow_mo=500
        )

    context_args = {"viewport": {"width": 1024, "height": 640}}
    if device:
        context_args.update(pw.devices[device])
    if geolocation:
        context_args["geolocation"] = geolocation
        context_args["permissions"] = ["geolocation"]
    context = browser.new_context(**context_args)
    page = context.new_page()
    return browser, context, page


def login_user_with_otp(page, email, email_extractor):
    page.get_by_role("textbox", name="Phone or email").fill(email)
    page.wait_for_timeout(1000)

    click_until_visible(page, 'button:has-text("Continue")', 'input[data-testid="validateCode"]', timeout=5)
   
    otp = None
    print("Waiting for OTP email...")
    page.wait_for_timeout(5000)  # Wait for email to arrive

    for i in range(30):
        print("Trying to fetch OTP from email, attempt:", i+1)
        otp = email_extractor.check_for_otp(email)
        if otp:
            print("OTP found in email:", otp)
            break
        print("No OTP found yet. Waiting for 3 seconds...")
        page.wait_for_timeout(3000)
    

    if not otp:
        print("No OTP found in unread emails.")
        return

    otp_input = page.locator('input[data-testid="validateCode"]')
    expect(otp_input).to_be_visible(timeout=10000)
    otp_input.fill(otp)


def login_and_initial_setup(page, email, is_logout = False, is_first = False):
    if is_first:
        page.goto(NEWDOT_URL)

    page.get_by_role("textbox", name="Phone or email").fill(email)
    page.wait_for_timeout(1000)

    continue_button = page.locator('button[tabindex="0"]')
    continue_button.wait_for(state="visible", timeout=10000)
    continue_button.click()
    
    page.wait_for_timeout(2000)
    
    try:
        page.locator('button[tabindex="0"]').click()
    except Exception:
        page.wait_for_timeout(1000)
        page.locator('button[tabindex="0"]').click()

    page.wait_for_timeout(2000)

    try:
        expect(page.get_by_text("want to do today")).to_be_visible(timeout=15000)
    except AssertionError:
        page.wait_for_timeout(1000)
        page.locator('button[tabindex="0"]').click()
    
    page.wait_for_timeout(2000)

    page.locator("text='Track and budget expenses'").wait_for(state="visible", timeout=10000)
    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()

    page.locator('input[name="fname"]').fill("Test")
    page.locator('input[name="lname"]').fill("User")
    page.get_by_role("button", name="Continue").last.click()
    page.wait_for_timeout(1000)

    if is_logout:
        page.get_by_label("My settings").click()
        page.wait_for_timeout(1000)
        page.get_by_label("Sign out").click()
        page.wait_for_timeout(1000)


def start_chat_and_send_file(page, emal_to_message):
    try:
        page.get_by_label("Start chat (Floating action)").click()
        page.get_by_label("Start chat", exact=True).click()
        page.wait_for_timeout(1000)

        page.get_by_test_id("selection-list-text-input").fill(emal_to_message)
        page.wait_for_timeout(1000)

        try:
            page.get_by_label("Test").click()
        except Exception:
            page.wait_for_timeout(1000)
            page.get_by_label(emal_to_message).click()

        page.wait_for_timeout(1000)

        page.get_by_label("Create").last.click()
        page.wait_for_timeout(1000)

        add_attachment = page.get_by_label("Add attachment")
        with page.expect_file_chooser() as file_chooser_info:
            add_attachment.click()

        page.wait_for_timeout(2000)
        
        file_chooser = file_chooser_info.value
        current_directory = os.getcwd()
        file_path = os.path.join(current_directory, "sample.pdf")
        file_chooser.set_files(file_path)
        page.wait_for_timeout(2000)

        page.get_by_role("dialog").get_by_role("button", name="Send").click()
        page.wait_for_timeout(2000)

        page.get_by_label("My settings").click()
        page.wait_for_timeout(1000)

        page.get_by_label("Sign out").click()
        page.wait_for_timeout(1000)


    except Exception as e:
        print(f"Error during workspace and chat setup: {e}")



def check_dowload_button(page):
    page.get_by_label("Navigates to a chat").last.click()
    page.wait_for_timeout(2000)


    page.context.set_offline(True)
    page.get_by_label("View attachment").first.click()
    download_button = 0

    try:
        download_button = page.get_by_label("Download").count()
    except:
        pass

    assert download_button == 0, "Download button is not hidden when offline, issue exists!"



def test_download_button_visibility():
    with sync_playwright() as pw:

        email_address = "rgarciatammy4@gmail.com"
        password = "ezkm eepd sctl nanx"


        email_extractor = IMAPOTPExtractor(email_address, password)
        email_1 = email_extractor.get_new_email_1()
        email_2 = email_extractor.get_new_email_2()

        browser, context, page = launch_app(pw)


        create_simple_pdf("sample.pdf")


        login_and_initial_setup(page, email_2, is_logout=True, is_first=True)
        context.clear_cookies()

        login_and_initial_setup(page, email_1)
        start_chat_and_send_file(page, email_2)

        login_user_with_otp(page, email_2, email_extractor)
        check_dowload_button(page)


        delete_pdf("sample.pdf")

        context.close()
        browser.close()
