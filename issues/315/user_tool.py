import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)


import os
import re
import email
import pytest
import imaplib
from PIL import Image
from playwright._impl._page import Page
from playwright.sync_api import sync_playwright, expect
from utils.trace_cleaner import trace_cleaner


BASE_EMAIL = "turingtemp+37299578@gmail.com"
PASSWORD = ""

class EmailHandler:
    def __init__(self, email_address, password):

        if not self._validate_email(email_address):
            raise ValueError("Invalid email address format.")
        self.original_email = email_address
        self.password = password





        self.new_email = self._generate_new_email(email_address, suffix="294711")
    
    def _validate_email(self, email_address):

        return bool(re.match(r"[^@]+@[^@]+\.[^@]+", email_address))
    
    def _generate_new_email(self, email_address, suffix):

        username, domain = "turingtemp@gmail.com".split('@')
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
        headless=True, slow_mo=1000, args=["--ignore-certificate-errors",
                              "--disable-web-security",
        "--disable-features=IsolateOrigins,site-per-process"]
    )
    context = browser.new_context()
    yield context  # Yield the page object to the test function
    browser.close()
    playwright.stop()



def login_user(page: Page, account: EmailHandler):

    user_email = account.get_email_address()
    page.goto("https://dev.new.expensify.com:8082/")

    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()

    try:
        expect(page.get_by_role("button", name="Sign in")).to_be_visible()
        page.get_by_test_id("validateCode").fill("179964")
    except Exception:
        page.get_by_role("button", name="Join").click()

    try:
        page.locator('button[tabindex="0"]').click()
    except:
        pass

def create_a_new_workspace(page, user_email):

    page.get_by_label("My settings").click()

    page.get_by_label("Workspaces").get_by_text("Workspaces").click()


    try:
        page.get_by_label("New workspace").click()
    except:
        page.get_by_label("New workspace").first.click() # In case there is no workspace yet
    
    try:
        return page.get_by_label(f"Test User's Workspace").inner_text().split('\n')[1]
    except:
        return page.get_by_label(f"Test User's Workspace").last.inner_text().split('\n')[1]  

def create_test_img(filename):
    width = 255
    height = 255


    img = Image.new('RGB', (width, height))


    for y in range(height):
        for x in range(width):

            r = x
            g = max(0, 255 - x - y)
            b = y
            img.putpixel((x, y), (r, g, b))


    img.save(filename)

def attachment_upload(page, filename="test-1.png"):
    page.get_by_label("Split expense").click()
    add_attachment = page.get_by_label("Choose file")

    with page.expect_file_chooser() as file_chooser_info:
        add_attachment.click()

    file_chooser = file_chooser_info.value

    create_test_img(filename)


    current_directory = os.getcwd()
    file_path = os.path.join(current_directory, filename)

    file_chooser.set_files(file_path)

    os.remove(filename)

def access_target_workspace_chat(page, chat_name):
    page.get_by_label("Back").first.click()
    page.get_by_label("Inbox").click()
    try:
        expect(page.locator("#root")).not_to_contain_text("Say hello!")
        expect(page.get_by_label("Chat welcome message")).not_to_contain_text("Welcome to #admins!")
        page.get_by_test_id("DisplayNamesWithTooltip").filter(has_text=re.compile(rf"^{chat_name}$")).last.click()
    except:
        page.get_by_test_id("DisplayNamesWithTooltip").filter(has_text=re.compile(rf"^{chat_name}$")).first.click()

@pytest.mark.parametrize("first_name, last_name", [("Test", "User")])
def test_selected_highlight(setup_playwright, first_name, last_name):
    context = setup_playwright
    context.tracing.start(screenshots=True, snapshots=True, sources=True)
    try:
        account = EmailHandler(email_address=BASE_EMAIL, password=PASSWORD)
        user_email = account.get_email_address()


        page = context.new_page()
        login_user(page, account)

        try:

            page.locator("text='Track and budget expenses'").click()
            page.get_by_role("button", name="Continue").click()


            page.locator('input[name="fname"]').fill("Test")
            page.locator('input[name="lname"]').fill("User")
            page.get_by_role("button", name="Continue").last.click()
        except:
            pass


        workspace_name = create_a_new_workspace(page, user_email)
        

        page.get_by_text("More features").click()
        page.get_by_label("Classify costs and track").click()

        page.get_by_test_id("WorkspaceInitialPage").get_by_text("Tags").click()

        try:
            page.get_by_label("Select all").click()
            page.get_by_text("2 selected").click()
            page.get_by_label("Delete tags").click()
            page.get_by_text("Delete").click()
        except:
            pass

        try:
            page.get_by_role("button", name="Add tag").click()
            page.get_by_role("textbox", name="Name").fill("first")
            page.get_by_role("button", name="Save").click()
            page.get_by_role("button", name="Add tag").click()
            page.get_by_role("textbox", name="Name").fill("second")
            page.get_by_role("button", name="Save").click()
        except:
            pass


        access_target_workspace_chat(page, workspace_name)


        page.get_by_label("Create").last.click()
        attachment_upload(page)
        page.get_by_role("menuitem", name="Tag").get_by_role("img").last.click()
        page.get_by_label("first").click()
        page.get_by_role("button", name="Split expense").click()

        page.get_by_label("Split").locator("img").click()
        page.get_by_label("first").click()

        page.get_by_label("second").click()

        page.get_by_test_id("SplitBillDetailsPage").get_by_label("second").click()
        tags_in_order = repr(page.get_by_test_id("IOURequestStepTag").get_by_test_id("selection-list").inner_text()).replace("'","").split('\\n')
        assert tags_in_order[0] == 'second', "Wrong tag."
    finally:
        context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
        trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
