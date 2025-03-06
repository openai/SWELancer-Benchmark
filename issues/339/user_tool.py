import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
import pytest
import time
import imaplib
import email
import re
from email.header import decode_header
from playwright.sync_api import sync_playwright, expect, Page
from utils.trace_cleaner import trace_cleaner


def get_magic_code(user_email, password, retries=5, delay=10):
    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    imap.login(user_email, password)
    magic_code = "123456"

    for attempt in range(retries):
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

        time.sleep(delay)

    imap.logout()
    print("Max retries reached. Email not found.")
    return magic_code


def login_user(page: Page, first_name="Yagna", last_name="Sai") -> tuple:
    user_email = "expensifysam@gmail.com"
    password = ""

    page.goto('https://dev.new.expensify.com:8082/') 
    phone_or_email_input = page.locator('input[type="email"]')
    expect(phone_or_email_input).to_be_visible()
    phone_or_email_input.fill(user_email)

    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(1000)


    magic_code = "123456"

    validate_code_input = page.locator('input[name="validateCode"]').nth(0)
    expect(validate_code_input).to_be_visible()
    validate_code_input.fill(magic_code)

    page.wait_for_timeout(1000)

@pytest.fixture
def setup_playwright(request):
    width = getattr(request, "param", {}).get("width", 1280)
    height = getattr(request, "param", {}).get("height", 720)

    playwright = sync_playwright().start()

    browser = playwright.chromium.launch(
        headless=True, slow_mo=500, args=[
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ]
    )

    context = browser.new_context(viewport={"width": width, "height": height})
    page = context.new_page()

    yield page


    browser.close()
    playwright.stop()


def wait_until_loader_disappears(page, selector, timeout=30):
    """
    Continuously checks for the presence of the loader every second.
    Exits when the loader is no longer present or when the timeout is reached.

    :param page: Playwright page object
    :param selector: The selector for the loader element
    :param timeout: Maximum time to wait before giving up (in seconds)
    """
    start_time = time.time()
    time.sleep(1)
    while True:

        loader_present = page.locator(selector).is_visible()

        if not loader_present:
            return True


        if time.time() - start_time > timeout:
            print("Timeout reached while waiting for the loader to disappear.")
            return False


        time.sleep(1)


def get_scroll_position(page, selector):
    """
    Retrieves the scrollTop (vertical scroll) and scrollLeft (horizontal scroll)
    of the given element.

    :param page: Playwright page object
    :param selector: The selector for the element to check the scroll position
    :return: A dictionary containing the scrollTop and scrollLeft positions
    """
    scroll_position = page.evaluate(
        """(selector) => {
        const elements = document.querySelectorAll(selector);
        const lastElement = elements[elements.length - 1];
        if (lastElement) {
            return {
                scrollTop: lastElement.scrollTop,
                scrollLeft: lastElement.scrollLeft
            };
        }
        return null;
    }""",
        selector,
    )
    return scroll_position

@pytest.mark.parametrize(
    "setup_playwright",
    [{"width": 1280, "height": 720}],
    indirect=True,
)
def test(setup_playwright):
    page = setup_playwright
    context = page.context
    context.tracing.start(screenshots=True, snapshots=True, sources=True)

    try:
        login_user(page)

        page.locator('button[aria-label="Start chat (Floating action)"]').click()
        page.locator('div[aria-label="Start chat"]').click()

        for i in range(15):
            page.get_by_test_id("selection-list-text-input").fill(
                f"testuser{i}@gmail.com"
            )
            success = wait_until_loader_disappears(page, 'div[role="progressbar"]')

        page.locator("#overLayBottomButton").click()
        page.get_by_label("My settings").click()
        page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()
        page.get_by_label("New workspace").first.click()

        page.locator('div[aria-label="Members"]').click()
        page.locator("button", has_text="Invite member").click()


        selector = '[data-testid="selection-list"]'

        initial_scroll_position = get_scroll_position(page, selector)
        print(f"Initial scroll position: {initial_scroll_position}")


        for _ in range(15):
            page.keyboard.press("ArrowDown")


        new_scroll_position = get_scroll_position(page, selector)
        print(f"New scroll position: {new_scroll_position}")


        assert (
            initial_scroll_position["scrollTop"] != new_scroll_position["scrollTop"]
        ), "The vertical scroll position remains the same!"

    except Exception as e:
        raise e

    finally:
        context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
        trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
