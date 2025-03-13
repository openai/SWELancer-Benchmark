import imaplib
import email
import re
from email.header import decode_header
from playwright.sync_api import sync_playwright, expect

GMAIL_NAME = "nomandevtur+54916.2"
GMAIL_APP_PASSWORD = "tpye xlsj axyq nltq"


def get_test_user_info(seed = None, first_name = None, last_name = None):
    if first_name is None:
        first_name = GMAIL_NAME

    if last_name is None:
        last_name = ""

    email = f"{GMAIL_NAME}+{seed}@gmail.com" if seed is not None else f"{GMAIL_NAME}@gmail.com"
    
    return {"email": email, "password": GMAIL_APP_PASSWORD, "first_name": first_name, "last_name": last_name}

def delete_email_inbox(user_email, password, retries=5, delay=10):
    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    imap.login(user_email, password)


    # Select inbox and delete all emails
    imap.select("inbox")
    status, all_emails = imap.search(None, "ALL")
    if status == "OK":
        for email_id in all_emails[0].split():
            imap.store(email_id, "+FLAGS", "\\Deleted")
        imap.expunge()


def get_magic_code(user_email, password, retries=5, delay=5):
    # Connect to the server
    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    imap.login(user_email, password)

    for _ in range(retries):
        imap.select("inbox")
        status, messages = imap.search(None, '(UNSEEN SUBJECT "Expensify magic sign-in code:")')

        if status == "OK":
            email_ids = messages[0].split()
            print(email_ids)

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

    

    imap.logout()
    print("Max retries reached. Email not found.")
    return None


def select_activity(page, first_name, last_name, activity_text):
    
    # Select activity in onboarding page and click Continue
    page.get_by_label(activity_text).click()

    # Enter first name, last name and click continue
    page.get_by_role("textbox", name="First name").fill(first_name)
    page.get_by_role("textbox", name="Last name").fill(last_name)
    page.get_by_role("button", name="Continue").last.click()


def login_user(page, user_info, activity_text="Track and budget expenses"):
    # Clear cookies, local storage, and session storage
    page.context.clear_cookies()

    page.goto('https://dev.new.expensify.com:8082/')
    page.wait_for_load_state('load')

    page.get_by_test_id("username").fill(user_info["email"])
    page.get_by_role("button", name="Continue").click()

    join_button = page.get_by_role("button", name="Join")
    validate_code_input = page.locator('input[data-testid="validateCode"]')

    page.wait_for_timeout(5000)
    if (join_button.is_visible()):
        join_button.click(timeout=3000)
    else:
        # magic_code = get_magic_code(user_info["email"], user_info["password"], retries=6, delay=5)

        # if magic_code is None:
        #     #Retrying again
        #     page.locator(f"span:has-text('Didn't receive a magic code?')").first.click()
        #     magic_code = get_magic_code(user_info["email"], user_info["password"], retries=6, delay=5)
        magic_code = "123456"
        print(f"Magic code: {magic_code}")
        validate_code_input.fill(magic_code)

    page.wait_for_timeout(3000)

    select_activity_dialog = page.get_by_text("What do you want to do today?")
    if select_activity_dialog.count() > 0:
        select_activity(page, user_info["first_name"], user_info["last_name"], activity_text)


def launch_app(pw, headless=False, device=None, geolocation=None):
    browser = pw.chromium.launch(headless = headless, 
                                proxy = {"server": "http://127.0.0.1:8080/"}, slow_mo = 1000,
                                args=[
                                    "--ignore-certificate-errors",
                                    "--disable-web-security", 
                                    "--disable-features=IsolateOrigins,site-per-process"
                                    ]
                            )

    context_args = {"viewport": {"width": 1124, "height": 740}}
    if device:
        context_args.update(pw.devices[device])
    if geolocation:
        context_args["geolocation"] = geolocation
        context_args["permissions"] = ["geolocation"]
    context = browser.new_context(**context_args)
    page = context.new_page()
    return browser, context, page

    
def test_54916():
    with sync_playwright() as p:
        
        user_info = get_test_user_info()

        delete_email_inbox(user_info["email"], user_info["password"], retries=6, delay=5)

        browser, context, page = launch_app(p)
        login_user(page, user_info)

        page.wait_for_timeout(3000)

        # prerequisite - One workspace should already be created with Rules enabled 
        page.get_by_label("My settings").click()
        page.wait_for_timeout(1000)
        page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()
        page.wait_for_timeout(1000)
        page.get_by_label("row").click()
        page.wait_for_timeout(1000)
        page.get_by_label("Rules").click()
        page.wait_for_timeout(1000)
        first_value = page.locator("div:has-text('$25.00')").last.inner_text()
        
        page.wait_for_timeout(1000)
        page.get_by_label("Categories").click()
        page.wait_for_timeout(1000)
        page.locator("#Advertising").click()
        second_value = page.locator("div:has-text('$25 • Default')").last.inner_text()

        # Assertion to ensure both extracted values contain "$25"
        assert "$25" in first_value and "$25" in second_value, f"Assertion failed! Values do not match: '{first_value}' vs '{second_value}'"


        page.wait_for_timeout(3000)
        page.close()
        browser.close()
