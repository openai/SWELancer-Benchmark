import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import pytest
import re
from playwright.async_api import async_playwright, expect, Page, TimeoutError
from utils.email_handler import get_unique_derived_email
from utils.trace_cleaner import trace_cleaner

async def connect_netsuite(accounting_page: Page):
    await accounting_page.get_by_label("NetSuite").get_by_role(
        "button", name="Connect"
    ).click()
    try:
        await accounting_page.locator("button", has_text="Upgrade").click(
            timeout=3000
        )
        await accounting_page.get_by_role(
            "button", name="Got it, thanks"
        ).click()
    except TimeoutError:
        pass

    workspace_id = re.search(
        r"settings/workspaces/([^/]+)/", accounting_page.url
    ).group(1)
    js_code = """
    () => {
    const net_suite = {
        "accountID": "TSTDRV1668486",
        "tokenID": "4WFxamEE2VzbjX/EN/Z9I5dFAOefKCdes1jtb1db87aATFz6T0pWt51jGFUJeYQFRdbrj6vIDbYLT/q+jW0cWXBLUcnV5CUqb2qsw4WVNlI=;kO0hlBNY1KxfPxZZTxJu/Q==;BXajerPTWHDHlPF/2NkKOHQP/cZ9zfuc3ENJN6u6K9/+KDtYxsPocN7JgZW10WDkGu5hL9YlMZSlY3tOBonSpw==",
        "options": {
            "data": {
                "subsidiaryList": [
                    {
                        "internalID": "1",
                        "country": "_unitedStates",
                        "isElimination": false,
                        "name": "Honeycomb Mfg."
                    },
                    {
                        "internalID": "3",
                        "country": "_unitedStates",
                        "isElimination": false,
                        "name": "Honeycomb Holdings Inc."
                    }
                ],
                "items": [
                    {
                        "name": "EST99999",
                        "id": "1006"
                    },
                    {
                        "name": "Expensify Invoice Expense",
                        "id": "1171"
                    },
                    {
                        "name": "Expensify Invoice Line Item",
                        "id": "1172"
                    }
                ],
                "payableList": [
                    {
                        "GL Code": "0805",
                        "name": "0805 Expensify Card Liability Ted Test",
                        "id": "3050",
                        "type": "_otherCurrentLiability"
                    },
                    {
                        "GL Code": "1000",
                        "name": "1000 Checking",
                        "id": "1",
                        "type": "_bank"
                    },
                    {
                        "GL Code": "1002",
                        "name": "1002 Savings",
                        "id": "2",
                        "type": "_bank"
                    }
                ],
                "taxAccountsList": [
                    {
                        "country": "_canada",
                        "name": "PST Expenses BC",
                        "externalID": "192"
                    }
                ]
            },
            "config": {
                "invoiceItemPreference": "create",
                "receivableAccount": "7",
                "taxPostingAccount": "",
                "exportToNextOpenPeriod": false,
                "allowForeignCurrency": true,
                "reimbursableExpensesExportDestination": "EXPENSE_REPORT",
                "subsidiary": "Honeycomb Mfg.",
                "syncOptions": {
                    "mapping": {
                        "classes": "REPORT_FIELD",
                        "jobs": "TAG",
                        "locations": "REPORT_FIELD",
                        "customers": "TAG",
                        "departments": "REPORT_FIELD"
                    },
                    "crossSubsidiaryCustomers": false,
                    "syncApprovalWorkflow": true,
                    "syncCustomLists": false,
                    "exportReportsTo": "REPORTS_APPROVED_NONE",
                    "exportVendorBillsTo": "VENDOR_BILLS_APPROVED_NONE",
                    "setFinalApprover": true,
                    "syncReimbursedReports": true,
                    "customSegments": [],
                    "syncPeople": false,
                    "enableNewCategories": true,
                    "hasChosenAutoSyncOption": true,
                    "finalApprover": "yuwen@expensify.com",
                    "syncTax": false,
                    "syncCustomSegments": false,
                    "customLists": [],
                    "syncCategories": true,
                    "hasChosenSyncReimbursedReportsOption": true,
                    "exportJournalsTo": "JOURNALS_APPROVED_NONE"
                },
                "autoCreateEntities": true,
                "exporter": "yuwen@expensify.com",
                "exportDate": "LAST_EXPENSE",
                "nonreimbursableExpensesExportDestination": "VENDOR_BILL",
                "reimbursablePayableAccount": "3050",
                "journalPostingPreference": "JOURNALS_POSTING_TOTAL_LINE",
                "invoiceItem": "1006",
                "subsidiaryID": "1",
                "defaultVendor": "42767",
                "provincialTaxPostingAccount": " ",
                "reimbursementAccountID": "1",
                "approvalAccount": "2000 Accounts Payable",
                "payableAcct": "3050",
                "customFormIDOptions": {
                    "reimbursable": {
                        "expenseReport": null
                    },
                    "nonReimbursable": {
                        "vendorBill": null
                    },
                    "enabled": false
                },
                "collectionAccount": "1"
            }
        },
        "verified": true,
        "lastSyncDate": "2024-11-08T05:56:40+0000",
        "lastErrorSyncDate": "",
        "source": "EXPENSIFYWEB",
        "config": {
            "autoSync": {
                "jobID": "5181292703454260454",
                "enabled": true
            }
        },
        "tokenSecret": "ibhjt36G3f5dmzje63CfEtS2DxpgB7ZXzx/7mcP3U33zx00P48RxQMAwN12JpsZChWNcN+t8YqjMdZiFRFae/CIwe0B7L0cbeiv2wSzxezc=;BRBh21nq9ogfckK+dFWYiQ==;TvupLzzkSWlB4lH/rtqDUF5wvVIyp40an3sYMsCpDu4txOiNT4f51oKGfXxgqN4JxgbzvDvGlNBciy3sSTR+9Q=="
    }

    Onyx.merge(`policy_WORKSPACE_ID`, {"connections":{
        "netsuite":net_suite
        }
    });
    }
    """.replace(
        "WORKSPACE_ID", workspace_id
    )

    await accounting_page.evaluate(js_code)
    await accounting_page.locator("#overLayBottomButton").click()

@pytest.mark.asyncio
async def test_send_invoice_workspace():
    async with async_playwright() as p:
        base_email = "namesomerandomemail@gmail.com"
        password = ""

        derived_email = get_unique_derived_email(base_email)
        derived_email = 'namesomerandomemail+1733924831@gmail.com'
        print(derived_email)

        browser = await p.chromium.launch(headless=True, args=[
            "--ignore-certificate-errors",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ], proxy={"server": "http://localhost:8080"}, slow_mo=500)


        context = await browser.new_context(viewport={"width": 1280, "height": 500})
        await context.tracing.start(title="trace", screenshots=True, snapshots=True, sources=True)

        page = await context.new_page()

        try:
            await page.goto('https://dev.new.expensify.com:8082/')


            phone_or_email_input = page.locator('input[type="email"]')
            await expect(phone_or_email_input).to_be_visible()
            await phone_or_email_input.fill(derived_email)


            continue_button = page.locator('button[tabindex="0"]')
            await expect(continue_button).to_be_visible()
            await continue_button.click()

            try:
                continue_button = page.locator('button[tabindex="0"]')
                await expect(continue_button).to_be_visible()
                await continue_button.click()
            except Exception:
                pass


            track_budget_option = page.locator("text=Track and budget expenses")
            await track_budget_option.click()


            await page.locator('input[name="fname"]').fill('Test')
            await page.locator('input[name="lname"]').fill('Test')
            await page.get_by_role("button", name="Continue").last.click()


            create_button = page.locator("[aria-label='Start chat (Floating action)']")
            await create_button.click()


            new_workspace_button = page.locator("[aria-label='New workspace']")
            await new_workspace_button.click()


            more_features_button = page.locator("text=More features")
            await more_features_button.click()


            invoice_button = page.locator("[aria-label='Sync your chart of accounts and more.']")
            await invoice_button.click()

            await page.locator("[aria-label='Accounting']").click()

            await connect_netsuite(page)

            await page.goto(f"{page.url}/netsuite/import/custom-segment/new")
            await page.get_by_label("Custom segment").click()
            await page.get_by_role("button", name="Next").click()
            await page.get_by_role("textbox", name="Name").press("CapsLock")
            await page.get_by_role("textbox", name="Name").fill("Posting")
            await page.get_by_role("button", name="Next").click()


            has_scroll_bar = await page.evaluate('''() => {
                const element = document.querySelector(".css-view-175oi2r.r-WebkitOverflowScrolling-150rngu.r-overflowY-1rnoaur");
                return element ? element.scrollHeight > element.clientHeight : false;
            }''')


            assert has_scroll_bar, "Expected div to have a scrollbar, but it does not."
        finally:

            await context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")

            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")

            await browser.close()
