import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
from io import BytesIO

from playwright.sync_api import Page, TimeoutError, sync_playwright


PASSWORD = "xqxz mmcb tvkn lpgp"
BASE_EMAIL = "testerbro7077@gmail.com"
POSTFIX = "48697"
PARTICIPANT_POSTFIX = "9nhP0hfC"


def create_in_memory_text_file():
    line = "This is a test file containing sample text.\n"
    text_content = line * 100 
    text_bytes = text_content.encode('utf-8')
    return BytesIO(text_bytes)


def generate_random_email(base_email=BASE_EMAIL, postfix=POSTFIX):
    email_user, domain = base_email.split("@")
    return f"{email_user}+{postfix}@{domain}"


def create_user(page: Page, firstname: str, lastname: str):
    page.get_by_role("button", name="Join").click()

    # Update profile
    page.get_by_text("Track and budget expenses").click()
    page.get_by_role("textbox", name="First name").fill(firstname)
    page.get_by_role("textbox", name="Last name").fill(lastname)
    page.get_by_role("button", name="Continue").click()


def login_or_create_user(
    page: Page, user_email: str, password: str, first_name: str, last_name: str
):
    page.get_by_test_id("username").fill(user_email)
    page.get_by_role("button", name="Continue").click()

    try:
        page.get_by_role("button", name="Join").wait_for(state="visible", timeout=2000)
        create_user(page, first_name, last_name)
    except TimeoutError:
        magic_code  = "123456"
        page.get_by_role("textbox").fill(magic_code)


def chat_attachment_upload(page,):
    filename = "test_file_1mb.txt"
    page.on("filechooser", lambda file_chooser: file_chooser.set_files([{
        "name": filename,
        "mimeType": "text/plain",
        "buffer": create_in_memory_text_file().getvalue()
    }]))

    page.get_by_label("Create").click()
    page.locator('div[aria-label="Add attachment"]').locator("visible=true").click()
    page.get_by_role("dialog").get_by_role("button", name="Send").click()

    page.wait_for_timeout(200)

    # Check for UI Stability
    if not is_ui_stable(page, filename):
        print("Screen blink detected.")
        assert False, "Screen blink detected. The UI changed significantly."
    else:
        print("No screen blink detected.")
        assert True, "No screen blink detected. The UI did not change significantly."


def is_ui_stable(page, filename, check_duration=5, interval=0.01):
    """Check if the UI is stable by monitoring the presence of the uploaded file's name."""
    initial_count = page.locator(
        f'div[data-testid="report-actions-list"] >> text={filename}'
    ).count()

    # Monitor the element count for `check_duration` seconds
    end_time = time.time() + check_duration
    while time.time() < end_time:
        current_count = page.locator(
            f'div[data-testid="report-actions-list"] >> text={filename}'
        ).count()
        if current_count != initial_count:
            # If the count changes, the UI is not stable
            return False
        time.sleep(interval)

    # If the count remains the same, the UI is stable
    return True


def close_button_if_present(page: Page):
    """
    Occasionally, there is a close button that prevents any clicks on the page as
    it covers most of the screen. This button cannot be seen visually.
    """
    close_button = page.locator('button[aria-label="Close"]')
    try:
        close_button.wait_for(timeout=2000)
        close_button.click()
    except TimeoutError:
        pass


def open_1_to_1(page: Page, participant_email: str):
    try:
        page.get_by_text("Hey there, I'm Concierge! If you have any").wait_for(
            state="visible", timeout=2000
        )
        page.get_by_label("Back").first.click()
    except TimeoutError:
        pass

    locator = page.locator(
        f'button[aria-label="Navigates to a chat"]:has-text("{participant_email}")'
    )

    try:
        # Wait up to 5 seconds, checking visibility repeatedly
        locator.wait_for(state="visible", timeout=5000)
        print("Opening 1:1 chat")
        # Open chat
        locator.click()
    except TimeoutError:
        print("No 1:1 chat to open, starting new chat")
        close_button_if_present(page)
        page.get_by_label("Start chat (Floating action)").click()
        page.get_by_label("Start chat", exact=True).click()
        page.get_by_test_id("selection-list-text-input").fill(participant_email)
        page.get_by_label(participant_email).click()


def test_run(first_name="Sai", last_name="Yagna"):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--ignore-certificate-errors",
                                                        "--disable-web-security",
                                                        "--disable-features=IsolateOrigins,site-per-process"], 
                                                        slow_mo=500)
        iphone_11 = p.devices["iPhone 11"]
        context = browser.new_context(**iphone_11)
        page = context.new_page()
        page.goto("https://dev.new.expensify.com:8082/")

        email = generate_random_email()
        participant_email = generate_random_email(postfix=PARTICIPANT_POSTFIX)
        login_or_create_user(page, email, PASSWORD, first_name, last_name)
        close_button_if_present(page)
        open_1_to_1(page, participant_email)
        chat_attachment_upload(page)

        browser.close()


if __name__ == "__main__":
    test_run()

