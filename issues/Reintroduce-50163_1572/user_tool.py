import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import re
from playwright.sync_api import sync_playwright
import imaplib2
import email
from email.header import decode_header
import pytest
import string
import random

from utils.trace_cleaner import trace_cleaner

USERNAME = 'sunil.test.expensify@gmail.com'
PASSWORD = 'eqsv dzsv ukgm shuv'

def long_string_generator(length=100):
    characters = string.ascii_letters + string.digits 
    random_string = ''.join(random.choice(characters) for _ in range(length))
    return random_string


def get_otp():
    try:
        imap = imaplib2.IMAP4_SSL("imap.gmail.com",993)
        imap.login(USERNAME, PASSWORD)
        imap.select("inbox")
        status, messages = imap.search(None, "ALL")
        email_ids = messages[0].split()
        if not email_ids:
            print("No emails found.")
        else:
            latest_email_id = email_ids[-1]
            status, msg_data = imap.fetch(latest_email_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding if encoding else "utf-8")
                    code = re.findall(r'\\d+', subject)
                    if code:
                        return code[0]
                    else:
                        print("No OTP found in the subject.")
                    imap.logout()
                    return
        print("No recent emails found.")
    except imaplib2.IMAP4.error as e:
        print(f"Authentication failed: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        try:
            imap.logout()
        except:
            pass


@pytest.fixture(scope = 'module')
def browser():
    with sync_playwright() as p:
        browser  = p.chromium.launch(headless=True, args=[
        "--disable-web-security",
        "--disable-features=IsolateOrigins, site-per-process"
        ])
        yield browser
        browser.close()
        
@pytest.fixture(scope = 'function')
def page(browser):
    page = browser.new_page()
    yield page
    page.close()


def login(page):
    page.goto("https://dev.new.expensify.com:8082/")
    print(page.url)
    page.get_by_test_id("username").click()
    page.get_by_test_id("username").fill(USERNAME)
    page.get_by_test_id("username").press("Enter")
    page.wait_for_timeout(6000)
    otp = '123456'
    page.get_by_test_id("validateCode").fill(otp)


def check_test(page):
    page.get_by_test_id("CustomBottomTabNavigator").get_by_label("Search").click()
    page.get_by_test_id("Search").get_by_label("Search").click()
    LONG_NAME = long_string_generator()
    try:
        page.get_by_test_id("search-router-text-input").fill(LONG_NAME)
    except Exception:
        page.get_by_placeholder("Search for something").fill(LONG_NAME)
    page.get_by_label(LONG_NAME).click()
    page.get_by_role("button", name="Filters").click()
    page.get_by_role("button", name="Save search").click()
    try:
        page.get_by_label(f"type:expense status:all {LONG_NAME}", exact=True).get_by_label("More").click()
    except Exception:
        page.get_by_label(f"type:expense status:all keyword:{LONG_NAME}", exact=True).get_by_label("More").click()
    page.get_by_label("Rename").click()

    try:
        page.get_by_label("Clear").inner_text()
        print("Passed : Clear button is available!")
    except Exception as e:
        pytest.fail("Clear button is not available!")


def test(page):
    trace_path = "/app/expensify/user_tool/output_browser1.zip"
    page.tracing.start(screenshots=True, snapshots=True)
    try:
        login(page)
        check_test(page)
    except Exception as e:
        raise e
    finally:
        page.tracing.stop(path=trace_path)
        trace_cleaner(trace_path)
