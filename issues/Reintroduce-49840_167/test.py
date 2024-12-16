import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
import imaplib
import email
from email.header import decode_header
import re

from playwright.sync_api import Page, expect, sync_playwright



GMAIL_NAME = "rgulraiz2000"
GMAIL_APP_PASSWORD = "kepw uquj myoa npvj"


def get_test_user_info(seed = None, first_name = None, last_name = None):
    if first_name is None:
        first_name = GMAIL_NAME

    if last_name is None:
        last_name = ""

    email = f"{GMAIL_NAME}+{seed}@gmail.com" if seed is not None else f"{GMAIL_NAME}@gmail.com"
    
    return {"email": email, "password": GMAIL_APP_PASSWORD, "first_name": first_name, "last_name": last_name}


def get_magic_code(user_email, password, retries=5, delay=5):
    # Connect to the server
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

                        # Search for the magic code in the subject
                        match = re.search(r"Expensify magic sign-in code: (\d+)", subject)
                        if match:
                            code = match.group(1)
                            imap.logout()
                            return code
            else:
                print("No unread emails found with the subject. Retrying...")
        else:
            print("Failed to retrieve emails. Retrying...")

        # Wait for the specified delay before trying again
        time.sleep(delay)

    imap.logout()
    print("Max retries reached. Email not found.")
    return None


def login_user(page, user_info, URL):
    page.goto(URL)
    page.wait_for_timeout(8000)

    page.get_by_role("textbox", name="Phone or email").click()
    page.get_by_role("textbox", name="Phone or email").fill(user_info["email"])
    page.get_by_role("button", name="Continue").click()
    page.wait_for_timeout(3000)

    join_button = page.get_by_role("button", name="Join")
    if (join_button.is_visible()):
        join_button.click(timeout=3000)
    else:
        # magic_code = get_magic_code(user_info["email"], user_info["password"], retries=6, delay=5)
        validate_code_input = page.locator('input[data-testid="validateCode"]')
        validate_code_input = page.locator('input[name="validateCode"]')
        validate_code_input = page.locator('input[autocomplete="one-time-code"][maxlength="6"]')
        magic_code = "000111"
        validate_code_input.fill(magic_code)

    page.wait_for_timeout(8000)

    if page.get_by_text("Track and budget expenses").is_visible():
        page.get_by_text("Track and budget expenses").click()
        page.get_by_role("textbox", name="First name").fill(user_info["first_name"])
        page.get_by_role("textbox", name="Last name").fill(user_info["last_name"])
        page.get_by_role("button", name="Continue").click()


def launch_browser():
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(channel="chrome",
    headless=True,
        args=[
                "--ignore-certificate-errors",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process"
            ],
            proxy={"server": "http://localhost:8080"},
            slow_mo=500
            )
    context = browser.new_context()
    page = context.new_page()
    
    return playwright, context, page

def create_new_workspace(page: Page):

    # go to settings
    page.get_by_label("My settings").click()

    # click on Workspaces
    page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").get_by_text("Workspaces").click()

    # create a new workspace
    page.get_by_role("button", name="New workspace").first.click()  
    page.get_by_label("Back").click()

    # change language
    page.get_by_text("Preferences").click()
    page.get_by_text("Language").click()
    page.get_by_label("Spanish").click()
    page.get_by_label("Recibidos").click()



def workspace_number(page:Page):
    # get the text that contains the Workspace number
    workspace_text = page.get_by_test_id("report-actions-list").last.inner_text()

    # Extract the number from the text
    match = re.search(r"\d+", workspace_text)
    number = match.group() if match else ""

    return number


def submit_expense(page, user_info):
    # create workspace and change language
    create_new_workspace(page)
    page.wait_for_timeout(5000)

    # select the newly created workspace
    number = workspace_number(page)
    page.wait_for_timeout(3000)
    workspace_locator = page.locator("button").filter(has_text=f"{user_info['first_name']} {user_info['last_name']}'s Workspace "+number)
    if workspace_locator.count() > 1:
        workspace_locator.first.click
    else:
        workspace_locator.click()

    page.get_by_label("Crear").last.click()
    page.get_by_text("Presentar gasto").click()
    page.get_by_label("Manual").click()
    page.get_by_placeholder("0").fill("5000")
    page.locator("#numPadContainerView").get_by_role("button", name="Siguiente").click()
    page.get_by_text("Obligatorio").click()
    page.get_by_role("textbox", name="Comerciante").fill("Test")
    page.get_by_role("button", name="Guardar").click()
    page.get_by_role("button", name="Solicitar 5000,00").click()
    page.get_by_label("Ver detalles").get_by_role("button").nth(1).click()
    
    de_otra_button = page.locator("div").filter(has_text="de otra")
    if de_otra_button.count() > 1:
        de_otra_button.first.click()
    
    assert not page.get_by_text("Payment complete").is_visible(), "Payment complete message is not in Spanish"

def test_user_session():
    """
    Demonstrate that the user session is not persisted across runs.
    """

    # Launch the browser
    playwright, context, page = launch_browser()

    # Login
    user_info = get_test_user_info(seed=753166,first_name="Turing", last_name="Alan")
    login_user(page, user_info, 'https://dev.new.expensify.com:8082/')

    # Necessary steps to reproduce the bug 
    submit_expense(page, user_info)

    context.close()
    playwright.stop()


