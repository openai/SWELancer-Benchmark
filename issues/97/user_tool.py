import json
from playwright.sync_api import sync_playwright
from urllib.parse import urlparse
from utils.trace_cleaner import trace_cleaner

def launch_browser(playwright):
    browser = playwright.chromium.launch(
            channel="chrome",
            headless=False,
            slow_mo=500,
            proxy={"server": "http://localhost:8080"},
            args=[
                "--ignore-certificate-errors",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process"
            ]
        )
    
    context = browser.new_context(timezone_id = "Asia/Karachi")
    page = context.new_page()

    return browser, page

def login_user(page, first_name="Test", last_name="User"):

    page.goto("https://dev.new.expensify.com:8082/")

    user_email = "freelancer.test.exp+1739641635@gmail.com"

    page.get_by_test_id("username").fill(user_email)
    page.get_by_role("button", name="Continue").click()
    page.get_by_role("button", name="Join").click()
    page.get_by_text("Track and budget expenses").click()
    page.get_by_role("button", name="Continue").click()
    page.get_by_role("textbox", name="First name").fill(first_name)
    page.get_by_role("textbox", name="Last name").fill(last_name)
    page.get_by_role("form").get_by_role("button", name="Continue").click()

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


def test_example():
    with sync_playwright() as playwright:
        browser, page = launch_browser(playwright)
        context = page.context
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        try:
            login_user(page)

            page.get_by_label("Start chat (Floating action)").click()
            page.get_by_label("New workspace").click()
            page.get_by_label("More features").click()
            page.get_by_label("Sync your chart of accounts").click()
            page.get_by_label("Accounting").click()

            workspace_url = urlparse(page.url)
            policy_id = workspace_url.path.split('/')[-2]

            page.evaluate(qbo_merge_code(policy_id))

            page.get_by_test_id("PolicyAccountingPage").get_by_label("Import").click()
            page.get_by_label("Imported as report fields").click()
            page.get_by_test_id("QuickbooksClassesPage").get_by_label("Report fields").click()
            page.get_by_test_id("selection-list").get_by_label("Report fields").click()
            page.get_by_role("button", name="Back").last.click()
            page.get_by_role("button", name="Back").last.click()
            page.get_by_role("button", name="Back").last.click()

            assert "https://dev.new.expensify.com:8082/settings/workspaces" == page.url

        finally:
            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            browser.close()


if __name__ == "__main__":
    test_example()