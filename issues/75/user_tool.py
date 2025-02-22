import os
import json
import re, time
from datetime import datetime, timezone
from email.header import decode_header
from PIL import Image
from io import BytesIO
import imaplib
import email
import re
from playwright.sync_api import Page, TimeoutError, expect, sync_playwright
import urllib.parse
from utils.trace_cleaner import trace_cleaner

USERNAME = "contributer0"
APP_PASSWORD = "ughk jfyj dyee mgrs"
USER_EMAIL = f"{USERNAME}+53114@gmail.com"
NEW_DOT_URL = "https://dev.new.expensify.com:8082/"


def get_magic_code(user_email, password, since=None, retries=5, delay=10):
    if since is None:
        since = datetime.now(timezone.utc).replace(second=0, microsecond=0)

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
                        email_date = email.utils.parsedate_to_datetime(msg["Date"])
                        if match and email_date >= since:
                            code = match.group(1)
                            imap.logout()
                            return code
                print("Email doesn't match conditions.  Retrying...")
            else:
                print("No unread emails found with the subject. Retrying...")
        else:
            print("Failed to retrieve emails. Retrying...")
        time.sleep(delay)

    imap.logout()
    print("Max retries reached. Email not found.")
    return None


def create_user(page: Page, firstname: str = "User", lastname: str = "Test"):
    page.get_by_role("button", name="Join").click()

    # Update profile
    page.get_by_text("Track and budget expenses").click()
    page.get_by_role("button", name="Continue").last.click()
    page.get_by_role("textbox", name="First name").fill(firstname)
    page.get_by_role("textbox", name="Last name").fill(lastname)

    try:
        page.get_by_role("button", name="Continue").click(timeout=2000)
    except TimeoutError:
        pass

    try:
        page.get_by_role("button", name="Get Started").click(timeout=200)
    except TimeoutError:
        pass


def login(page: Page):
    # get current timestamp
    magic_code = "123456"

    if magic_code is None:
        raise ValueError("Failed to retrieve magic code")
    page.get_by_role("textbox").fill(magic_code)


def login_or_create_user(
    page: Page, user_email: str = USER_EMAIL, lastname: str = "Test"
):
    page.get_by_role("textbox", name="Phone or email").fill(user_email)
    page.get_by_role("button", name="Continue").click()

    try:
        page.get_by_role("button", name="Join").wait_for(state="visible", timeout=2000)
        create_user(page, lastname)
    except TimeoutError:
        login(page)

    page.get_by_label("Inbox").first.wait_for(state="visible")


def qbo_merge_code(policy_id):

    qbo_data = {
        "connections": {
            "quickbooksOnline": {
                "config": {
                    "companyName": "test",
                    "credentials": {
                        "access_token": "2LHOKnH9waofJaMRyrVBUP+4qJsh4u+6E3Ffu73YJFJ6FnzAfsydZVkVFwjQmyxknEXCOYNeqoRljafcUk2sgzeq6002fXY55AEKF36UjaQQskfo4wR192K0v/68BUEzCpghfahoRmupoNq0u1JM8h/NDNIcLEi9ZDBno+7a22wi2jshJtcGL/wGBMUalWFupOmkiJbLPFen+mHFqLI8kF4TydI2a7SC4M4BAkZ2N7cFvp9LC39cLvrL7pZ/0wdIe8d4AMrKdR8M8V+KD8r2X4zXoQhKxSPA+2wRFiXIwOKB2iZqgI19dQHD0QqwbW6a512nOb7Q1Y0/SrF6NtVAaBXwhF2o3VULwFH3cy4QTYxB25wXCU76bhYsvUaQ/xWUVjY2TEi3GXkdTrNN8Ys8MXH3A9kVX7I32whBMfygcjYLtxc4/aVr8gYg8w5XPRRJ5Q/OGy68mX1JlCyWi+1NNAUJVkeRXuOsnivYvvaRisCJ4bng4ZiK9hnSWJ6qyKMWnb/nPpjZfZe25nbXfEG/e3CgwJ3KU4RlWZM+ECSWGcM/KyAGfErbcDBXXQk/6BnMjTqQkP5HotH8BHsUzYsw8D1A8i3gpgU/CStK8b+2PFcoqgTxWmsPgL7O32AFNR6z1yd1Zsrk5cDVHDlTddw1ePxrvfJRuT7gNKlut9oIAjgyR5iagxk/By2AGp0o2S53becAoPRGtuYYxk5WmpfB2q0N0QHI9VtRDJ5p1wn4KPO4twnnkU5YyD/u2UuBCWw9UB1rDWZVpGRUilyF2/0vy7PJHoUCXodz0DIulT+cDSHqf9hmc1pm7LI3Qt17X4uO1YCIQA7qQk1G5aY32HwNVq2VnyZJT64nEJ3JMydI4k74jrGy9Zp+52lAF39AenCaNjbVJg5svd0KEeOdwqr1j9SNkrHZkMmhuAUSI/WfyAhrtmjmRVGBTJ6b9l8fjdzwLwubXdFInG8M7h8Pc0Db7VTvd8Qv8MFRjhomzHbTkVMApKr1EH9WGzf932FlDse9HwKC4c6mA2Uj0BCaxsbnKnqd/I6Ug==;vJoXwrJgPzNOdv28yQHtPA==;eKPhE8t3aDV62W1np/MZoKIYA1bRawdFuttb5yxT44HQWjYgEc5x/Glx+Ye6YZP06Aj3N0A7eMw6rj98Kjpaow==",
                        "companyID": "934145206296",
                        "companyName": "test",
                        "expires": 1730725016,
                        "realmId": "934145340296",
                        "refresh_token": "KwizVqdImwI5kHeImQ2NrXO7rteCSzvtQakR3uhp7Y04X06z3F4Hvt42jw==;fK/XjysVFPC4lYgRXbzi/RpxI1z3aWWpaLSAnT5v1kRtg4ilXX9fjQvA6Wc3LhKqZXnADugm2DbveEmZWAItlg==",
                        "scope": "Accounting",
                        "token_type": "bearer"
                    },
                    "realmId": "9341453405206",
                    "autoSync": {
                        "enabled": True,
                        "jobID": "4604867689969023701"
                    },
                    "syncClasses": "REPORT_FIELD",
                    "pendingFields": {},
                    "errorFields": {},
                    "syncLocations": "NONE",
                    "autoCreateVendor": False,
                    "collectionAccountID": "29",
                    "enableNewCategories": True,
                    "export": {
                        "exporter": "zhenja3033@gmail.com"
                    },
                    "exportDate": "REPORT_EXPORTED",
                    "hasChosenAutoSyncOption": True,
                    "lastConfigurationTime": 1730721696740,
                    "markChecksToBePrinted": False,
                    "nonReimbursableBillDefaultVendor": "NONE",
                    "nonReimbursableExpensesAccount": {
                        "currency": "PLN",
                        "glCode": "",
                        "id": "29",
                        "name": "Cash and cash equivalents"
                    },
                    "nonReimbursableExpensesExportDestination": "debit_card",
                    "reimbursableExpensesAccount": {
                        "currency": "PLN",
                        "glCode": "",
                        "id": "29",
                        "name": "Cash and cash equivalents"
                    },
                    "reimbursableExpensesExportDestination": "bill",
                    "reimbursementAccountID": "29",
                    "syncCustomers": "TAG",
                    "syncItems": False,
                    "syncPeople": False,
                    "syncTax": False
                },
                "data": {
                    "accountPayable": [],
                    "accountsReceivable": [],
                    "bankAccounts": [
                        {
                            "currency": "PLN",
                            "glCode": "",
                            "id": "29",
                            "name": "Cash and cash equivalents"
                        },
                        {
                            "currency": "PLN",
                            "glCode": "",
                            "id": "30",
                            "name": "Test 1234"
                        }
                    ],
                    "country": "PL",
                    "creditCards": [],
                    "edition": "QuickBooks Online Simple Start",
                    "employees": [],
                    "homeCurrency": "PLN",
                    "isMultiCurrencyEnabled": False,
                    "journalEntryAccounts": [
                        {
                            "currency": "PLN",
                            "glCode": "",
                            "id": "32",
                            "name": "Accrued liabilities"
                        },
                        {
                            "currency": "PLN",
                            "glCode": "",
                            "id": "70",
                            "name": "Allowance for bad debt"
                        },
                        {
                            "currency": "PLN",
                            "glCode": "",
                            "id": "13",
                            "name": "Available for sale assets (short-term)"
                        },
                        {
                            "currency": "PLN",
                            "glCode": "",
                            "id": "38",
                            "name": "Dividends payable"
                        },
                        {
                            "currency": "PLN",
                            "glCode": "",
                            "id": "26",
                            "name": "Income tax payable"
                        },
                        {
                            "currency": "PLN",
                            "glCode": "",
                            "id": "65",
                            "name": "Inventory"
                        },
                        {
                            "currency": "PLN",
                            "glCode": "",
                            "id": "74",
                            "name": "Payroll Clearing"
                        },
                        {
                            "currency": "PLN",
                            "glCode": "",
                            "id": "73",
                            "name": "Payroll liabilities"
                        },
                        {
                            "currency": "PLN",
                            "glCode": "",
                            "id": "47",
                            "name": "Prepaid expenses"
                        },
                        {
                            "currency": "PLN",
                            "glCode": "",
                            "id": "71",
                            "name": "Short-term debit"
                        },
                        {
                            "currency": "PLN",
                            "glCode": "",
                            "id": "1",
                            "name": "Uncategorised Asset"
                        }
                    ],
                    "otherCurrentAssetAccounts": [
                        {
                            "currency": "PLN",
                            "glCode": "",
                            "id": "70",
                            "name": "Allowance for bad debt"
                        },
                        {
                            "currency": "PLN",
                            "glCode": "",
                            "id": "13",
                            "name": "Available for sale assets (short-term)"
                        },
                        {
                            "currency": "PLN",
                            "glCode": "",
                            "id": "65",
                            "name": "Inventory"
                        },
                        {
                            "currency": "PLN",
                            "glCode": "",
                            "id": "47",
                            "name": "Prepaid expenses"
                        },
                        {
                            "currency": "PLN",
                            "glCode": "",
                            "id": "1",
                            "name": "Uncategorised Asset"
                        }
                    ],
                    "vendors": []
                },
                "lastSync": {
                    "errorDate": "",
                    "errorMessage": "",
                    "isAuthenticationError": False,
                    "isConnected": True,
                    "isSuccessful": True,
                    "source": "NEWEXPENSIFY",
                    "successfulDate": "2024-11-04T12:01:36+0000"
                }
            }
        }
    }

    qbo_json = json.dumps(qbo_data)

    return f'Onyx.merge("policy_{policy_id}", {qbo_json})'


def test_53114():
    with sync_playwright() as p:

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
            slow_mo=500
        )
        context = browser.new_context()

        # Start tracing
        context.tracing.start(screenshots=True, snapshots=True, sources=True)

        page = context.new_page()

        try:
            # Login Expensify
            page.goto(NEW_DOT_URL)
            login_or_create_user(page)

            # go to Settings
            page.get_by_label("My settings").click()

            # go workspace
            page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()
            page.get_by_label("row").click()

            # click on Accounting
            page.get_by_label("Accounting").click()

            # get workspace id
            workspace_url = urllib.parse.urlparse(page.url)
            policy_id = str(workspace_url.path.split('/')[-2])
            # policy_id = "4BC155E6C950A85F"
            page.wait_for_timeout(1000)

            # Apply the patch for Quickbooks Online to connect https://openaihumans.slack.com/archives/C07KY1LMXEF/p1739650747578869
            page.evaluate(qbo_merge_code(policy_id))

            page.wait_for_timeout(1000)
            
            # Go to Advanced
            page.get_by_label("Advanced").click()
            
            # Click on QuickBooks invoice collections account
            page.get_by_text("QuickBooks invoice collections accountCash and cash equivalents").click()
            
            update_api_called = False

            # Listen for network requests
            def check_request(request):
                nonlocal update_api_called
                if "UpdateQuickbooksOnlineCollectionAccountID" in request.url and request.method == "POST":  
                    update_api_called = True

            page.on("request", check_request)

            # Select the same value already selected
            page.get_by_test_id("selection-list").get_by_label("Cash and cash equivalents").click()

            # Assert that no update request was made
            assert not update_api_called, "Update API call was unexpectedly made!"
        finally:
            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            context.tracing.stop(path=trace_path)
            trace_cleaner(trace_path)
            browser.close()


if __name__ == '__main__':
    test_53114()