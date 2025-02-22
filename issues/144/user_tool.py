import time
from playwright.sync_api import sync_playwright
import email
from email.header import decode_header
import imaplib
import re
import random
from utils.trace_cleaner import trace_cleaner

original_email = "nitish.expensify@gmail.com"
APP_PASSWORD = "ojhi eovp lbkz ktfb"


def get_updated_url(url):
    if url.endswith('.'):
        url = url[:-1]

    match = re.search(r'\.com(.*)', url)
    if match:
        extracted_text = match.group(1)
    else:
        return "Invalid URL format"

    parts = extracted_text.rsplit('/', 1)
    if len(parts) == 2 and parts[1].isdigit():
        number_part = parts[1]
        last_char = number_part[-1]

        possible_numbers = [str(i) for i in range(10) if str(i) != last_char]
        new_last_char = random.choice(possible_numbers)

        modified_number = number_part[:-1] + f'**{new_last_char}**'
        modified_text = f"{parts[0]}/{modified_number}"
    else:
        return "Invalid number format in URL"

    return f"https://dev.new.expensify.com:8082{modified_text}"


def clear_inbox():
    with imaplib.IMAP4_SSL(host="imap.gmail.com") as imap:
        imap.login(original_email, APP_PASSWORD)
        imap.select("inbox")
        imap.store("1:*", "+FLAGS", "\Deleted")
        imap.expunge()
        imap.close()


def get_magic_link(retries=5, delay=10):
    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    imap.login(original_email, APP_PASSWORD)

    for _ in range(retries):
        imap.select("inbox")
        status, messages = imap.search(
            None, '(UNSEEN SUBJECT "Expensify magic sign-in code:")')

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

                        # Get the email content
                        if msg.is_multipart():
                            for part in msg.walk():
                                content_type = part.get_content_type()
                                content_disposition = str(part.get("Content-Disposition"))

                                if "text/plain" in content_type and "attachment" not in content_disposition:
                                    body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                                    break
                        else:
                            body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")

                        # Extract the magic link
                        link_match = re.search(r"(https?://[^\s]+)", body)
                        if link_match:
                            magic_link = link_match.group(1)
                            imap.logout()
                            return magic_link

            else:
                print("No unread emails found with the subject. Retrying...")
        else:
            print("Failed to retrieve emails. Retrying...")
        time.sleep(delay)

    imap.logout()
    print("Max retries reached. Email not found.")
    return None


def login_user(pw):
    # clear_inbox()
    browser = pw.chromium.launch(proxy={"server": "http://localhost:8080"}, headless=False, args=[
        "--no-sandbox", "--disable-dev-shm-usage", "--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"], slow_mo=3000, channel="chromium")
    context_args = {}
    context_args["timezone_id"] = "Asia/Calcutta"

    context1 = browser.new_context(**context_args)
    # Start tracing on context1
    context1.tracing.start(screenshots=True, snapshots=True, sources=True)
    page1 = context1.new_page()
    user_email = "nitish.expensify+12365424@gmail.com"

    page1.goto('https://dev.new.expensify.com:8082/')

    page1.locator('input[type="email"]').fill(user_email)
    page1.get_by_role("button", name="Continue").click()
    # magic_link = get_magic_link()
    # updated_url = get_updated_url(magic_link)

    context2 = browser.new_context(**context_args)
    # Start tracing on context2
    context2.tracing.start(screenshots=True, snapshots=True, sources=True)
    page2 = context2.new_page()
    page2.goto("https://dev.new.expensify.com:8082/v/19159716/90003**2**", timeout=300000)

    return page2, browser, context1, context2


def test_the_issue():
    with sync_playwright() as p:
        page = None
        browser = None
        context1 = None
        context2 = None
        try:
            page, browser, context1, context2 = login_user(p)
            assert page.get_by_text("Oops, this page cannot be found").is_visible(), "Here's your magic code is visible!"
        finally:
            # Stop tracing, export trace files and call trace_cleaner for each context
            if context1 is not None:
                trace_path1 = "/app/expensify/user_tool/output_browser1.zip"
                context1.tracing.stop(path=trace_path1)
                trace_cleaner(trace_path1)
            if context2 is not None:
                trace_path2 = "/app/expensify/user_tool/output_browser2.zip"
                context2.tracing.stop(path=trace_path2)
                trace_cleaner(trace_path2)
            if browser is not None:
                browser.close()


test_the_issue()
