import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import email
from email.header import decode_header
import imaplib
from playwright.sync_api import sync_playwright
import re
import unittest
import time

from utils.trace_cleaner import trace_cleaner

class TestSuite(unittest.TestCase):
    @classmethod
    def setUp(cls):
        cls.username = 'testemail.ameen' # Email username
        email = cls.generate_random_email()
        cls.password = "yjsp jfez uvmy gkgs" # App password
        cls.url = 'https://dev.new.expensify.com:8082/'

        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(headless=True,args=[
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
            ],
        )
        cls.context = cls.browser.new_context()
        cls.page = cls.context.new_page()
        cls.page.goto(
            cls.url,
            timeout=60000)
        cls.login_account(email)

    @classmethod
    def tearDown(cls):

        cls.page.close()
        cls.context.close()
        cls.browser.close()
        cls.playwright.stop()

    @classmethod
    def login_account(cls, email, first_name='Test', last_name='User', context_page=None):
        page = page = context_page if context_page else cls.page



        page.locator('input[type="email"]').fill(email)
        page.locator('button[tabindex="0"]').click(timeout=10000)


        try:  
            page.wait_for_selector("text=Please enter the magic code sent to", timeout=5000)
            cls.existing_login=True
            expensify_opt = cls.get_magic_code(email, cls.password) # Get OTP
            page.locator('input[inputmode="numeric"]').fill(expensify_opt)
            page.wait_for_selector('button[tabindex="0"]:has-text("Sign in")', timeout=15000)
        except:
            page.wait_for_selector('button[tabindex="0"]:has-text("Join")', timeout=15000) 
            page.locator('button[tabindex="0"]:has-text("Join")').click()
            try:
                page.locator("text='Track and budget expenses'").click()
                page.get_by_role("button", name="Continue").click()
                page.locator('input[name="fname"]').wait_for(state="visible", timeout=10000)
                page.locator('input[name="fname"]').fill(first_name)
                page.locator('input[name="lname"]').fill(last_name)
                page.get_by_role("button", name="Continue").click()
            except:
                pass

    @classmethod
    def generate_random_email(cls):
        timestamp = int(time.time())
        return f"{cls.username}0984090740@gmail.com"

    @classmethod
    def get_magic_code(cls, user_email, password, retries=5, delay=8000):
        cls.page.wait_for_timeout(delay)
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
        cls.page.wait_for_timeout(delay)

        imap.logout()
        print("Max retries reached. Email not found.")
        return None

    @classmethod
    def click_element(cls, selectors_or_locator, context_page=None):

        page = context_page if context_page else cls.page


        if isinstance(selectors_or_locator, list):
            element = page.locator(selectors_or_locator[0])
            for selector in selectors_or_locator[1:]:
                element = element.locator(selector)

        elif isinstance(selectors_or_locator, str):
            element = page.locator(selectors_or_locator)

        else:
            element = selectors_or_locator

        element.wait_for(state="visible", timeout=10000)
        element.click()

    @classmethod
    def navigate_with_tabs(self, tab_count, enter=True, context_page=None):
        page = context_page if context_page else self.page

        self.page.wait_for_timeout(1000)
        page.bring_to_front()

        for _ in range(tab_count):
            page.keyboard.press("Tab")
        if enter:
            page.keyboard.press("Enter")
    
    @classmethod
    def start_group_chat(cls):
        page = cls.page
        cls.click_element('button[aria-label="Start chat (Floating action)"]')
        cls.click_element('div[aria-label="Start chat"][role="menuitem"]')
        page.locator('input[aria-label="Name, email, or phone number"]').fill('testuser@gmail.com')
        cls.navigate_with_tabs(2) # Select User
        cls.click_element('button:has-text("Next")')
        cls.click_element('button:has-text("Start group")')

    @classmethod
    def create_task(cls):
        page = cls.page
        cls.click_element(
                page.locator('button[aria-label="Create"]').nth(1)
            )
        cls.click_element(page.get_by_text("Assign task"))
        page.locator('input[aria-label="Title"]').fill("Test Task")
        cls.click_element(
                page.locator("button", has_text="Next")
            )
        cls.click_element(page.get_by_role("button", name="Confirm task"))


    def test_task_checkbox_center_vertically_with_title(self):
        trace_path = "/app/expensify/user_tool/output_browser1.zip"
        self.context.tracing.start(screenshots=True, snapshots=True, sources=True)
        try:
            page = self.page




            self.start_group_chat()




            self.create_task()




            page.wait_for_timeout(2000)
            task_checkbox = page.get_by_role("checkbox", name="Task").bounding_box()
            task_title = page.get_by_role("button", name="Task").bounding_box()

            checkbox_height = task_checkbox['height']
            title_height = task_title['height']


            if task_title['height'] == 24:
                task_title = page.get_by_role("button", name="Task").locator('div').nth(1).bounding_box()
                title_height = task_title['height']
                
            assert task_checkbox['height'] == task_title['height'] , f"Task title and checkbox heights are not the same: {checkbox_height} != {title_height}"

        except Exception as e:
            self.fail(f"Test failed due to error: {str(e)}")
        finally:
            self.context.tracing.stop()
            self.context.tracing.export(path=trace_path)
            trace_cleaner(trace_path)

if __name__ == "__main__":
    unittest.main(verbosity=2)
