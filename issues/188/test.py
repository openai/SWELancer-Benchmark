import time
from playwright.sync_api import Page, sync_playwright, expect


EXPENSIFY_URL = "https://dev.new.expensify.com:8082/"
FIRST_NAME = "Asaad"
LAST_NAME = "I"
TASK_TITLE = "Task"
CURRENCY = "USD"
CURRENCY_SYMBOL = "$"
INITIAL_EXPENSE_AMOUNT = "10"
EDITED_EXPENSE_AMOUNT = "20"
CHECK_EXPENSE_AMOUNT = "30"
SLOW_MO = 500
PROXY_SERVER = "http://localhost:8080"


def generate_random_email(username="expensify66", domain="gmail.com", seed=None):
    if seed is None:
        seed = int(time.time())
    return f"{username}+{seed}@{domain}"


def login(page: Page):
    # Step 1: Open expensify url
    page.goto(EXPENSIFY_URL)

    email = generate_random_email()

    # Step 2: Enter email and click continue
    page.get_by_test_id("username").fill(email)
    page.get_by_role("button", name="Continue").click()

    # Step 3: Click join button
    page.get_by_role("button", name="Join").click()

    # Step 4: Select 'Track and budget expenses' in onobarding page and click Continue
    page.get_by_text("Track and budget expenses").click()
    page.get_by_role("button", name="Continue").click()

    # Step 5: Enter first name, last name and click continue
    page.get_by_role("textbox", name="First name").fill(FIRST_NAME)
    page.get_by_role("textbox", name="Last name").fill(LAST_NAME)
    page.get_by_role("form").get_by_role("button", name="Continue").click()

    # Step 6: Get ahead of welcome to expensify by clicking get started
    try:
        page.get_by_role("button", name="Get started").last.click(timeout=3000)
    except:
        # ignore the error  and proceed
        pass


def verify_track_expense_amount(page: Page):
    # Step 1: Open Personal Chat
    page.get_by_label("Navigates to a chat").get_by_text(
        f"{FIRST_NAME} {LAST_NAME} (you)"
    ).click()

    # step 2: track expense with initial amount
    report_locator = page.get_by_test_id(f"report-screen-{page.url.split('/')[-1]}")
    report_locator.get_by_label("Create").click()
    page.get_by_label("Track expense").click()
    page.get_by_label("Manual").click()
    page.get_by_label("Select a currency").click()
    page.get_by_test_id("selection-list-text-input").fill(CURRENCY)
    page.get_by_label(CURRENCY).click()
    page.get_by_placeholder("0").fill(INITIAL_EXPENSE_AMOUNT)
    page.locator("#numPadContainerView").get_by_role("button", name="Next").click()
    page.get_by_test_id("IOURequestStepConfirmation").get_by_role(
        "button", name="Track expense"
    ).click()

    # step 3: edit expense amount
    report_locator.get_by_text("Cash$").click()
    page.get_by_role("menuitem", name="$").get_by_role("img").click()
    page.get_by_placeholder("0").fill(EDITED_EXPENSE_AMOUNT)
    page.locator("#numPadContainerView").get_by_role("button", name="Save").click()
    page.go_back()

    # step 4: Click on submit it to someone and edit expense amount
    report_locator.get_by_role("button", name="Submit it to someone").click()
    chat_email = generate_random_email()
    page.get_by_test_id("selection-list-text-input").fill(chat_email)
    page.get_by_label(chat_email).click()
    page.get_by_test_id("IOURequestStepConfirmation").get_by_label(
        CURRENCY_SYMBOL
    ).click()
    page.get_by_placeholder("0").fill(CHECK_EXPENSE_AMOUNT)
    page.locator("#numPadContainerView").get_by_role("button", name="Save").click()

    # step 5: verify that expense amount is updated
    page.get_by_test_id("IOURequestStepConfirmation").get_by_label(
        CURRENCY_SYMBOL
    ).click()
    expect(
        page.get_by_test_id("IOURequestStepAmount").get_by_text(
            f"{CURRENCY_SYMBOL}{CHECK_EXPENSE_AMOUNT}"
        ),
        f"Expense amount is not updated to {CURRENCY_SYMBOL}{CHECK_EXPENSE_AMOUNT}",
    ).to_be_visible()


def test_track_expense_amount():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            slow_mo=SLOW_MO,
            args=(
                [
                    "--ignore-certificate-errors",
                    "--disable-web-security",
                    "--disable-features=IsolateOrigins,site-per-process",
                ]
                if PROXY_SERVER
                else None
            ),
            proxy={"server": PROXY_SERVER} if PROXY_SERVER else None,
        )
        context = browser.new_context()
        page = context.new_page()

        # Step 1: Login to expensify
        login(page)

        # Step 2: Verify that expense amount is updated
        verify_track_expense_amount(page)

        # Step 3: Cleanup
        page.close()
        context.close()
        browser.close()
