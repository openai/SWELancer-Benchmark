import os
from playwright.sync_api import sync_playwright


# Expensify app URL
EXPENSIFY_URL = "https://dev.new.expensify.com:8082/"

# Email login credentials
EMAIL_USERNAME = "naturesv057+54640_1@gmail.com"

def launch_browser(pw, device=None, geolocation=None):
    """
    Launch the browser.
    """
    browser = pw.chromium.launch(
        proxy = {"server": "http://localhost:8080"}, headless = False, args = ["--no-sandbox", "--disable-dev-shm-usage", "--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"], slow_mo = 500, channel = "chromium")
    context_args = {}
    if device:
        context_args.update(pw.devices[device])
    if geolocation:
        context_args["geolocation"] = geolocation
        context_args["permissions"] = ["geolocation"]
    context = browser.new_context(**context_args)
    page = context.new_page()
    return browser, context, page


def login_user(page):
    """
    Login to the Expensify app and complete the onboarding.
    """
    # Open the Expensify app
    page.goto(EXPENSIFY_URL)

    # Login user
    page.get_by_role("textbox", name="Phone or email").fill(EMAIL_USERNAME)
    page.locator("div", has_text="Continue").last.click()
    
    # Get the OTP code from the email
    otp = "123456"
    
    # Enter the OTP code
    page.keyboard.type(otp)


def create_simple_pdf(filename="sample.pdf"):
    """
    Creates a simple PDF file in the current working directory without using any external libraries.
    
    Args:
    - filename (str): The name of the PDF file to be created.
    
    Returns:
    - str: The absolute path of the created PDF file.
    """
    pdf_content = """%PDF-1.4
    1 0 obj
    << /Type /Catalog /Pages 2 0 R >>
    endobj
    2 0 obj
    << /Type /Pages /Kids [3 0 R] /Count 1 >>
    endobj
    3 0 obj
    << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << >> >>
    endobj
    4 0 obj
    << /Length 44 >>
    stream
    BT
    /F1 24 Tf
    100 700 Td
    (Hello, this is a simple PDF file) Tj
    ET
    endstream
    endobj
    5 0 obj
    << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
    endobj
    xref
    0 6
    0000000000 65535 f 
    0000000010 00000 n 
    0000000079 00000 n 
    0000000178 00000 n 
    0000000328 00000 n 
    0000000407 00000 n 
    trailer
    << /Size 6 /Root 1 0 R >>
    startxref
    488
    %%EOF
    """

    # Write the raw binary PDF data to the file
    with open(filename, "wb") as file:
        file.write(pdf_content.encode('latin1'))  # PDF requires Latin-1 encoding
    
    return filename


def delete_pdf(filename="sample.pdf"):
    """
    Deletes a PDF file in the current working directory.
    
    Args:
    - filename (str): The name of the PDF file to be deleted.
    
    Returns:
    - bool: True if the file was successfully deleted, False if the file does not exist.
    """
    file_path = os.path.join(os.getcwd(), filename)
    
    if os.path.exists(file_path):
        os.remove(file_path)
        return True
    else:
        print(f"File not found, could not delete: {file_path}")
        return False

def upload_attachment(page):
    # Create a pdf file
    filename = "sample.pdf"
    create_simple_pdf("sample.pdf")

    edit_text_button = page.locator('div[aria-label="Add attachment"]').locator("visible=true")
    
    with page.expect_file_chooser() as file_chooser_info:
        edit_text_button.click()
    page.wait_for_timeout(3000)
    file_chooser = file_chooser_info.value
    file_path = os.path.join(os.getcwd(), filename)
    file_chooser.set_files(file_path)
    page.wait_for_timeout(2000)

    page.locator('button:has-text("Send")').click()
    page.wait_for_timeout(2000) 
    return page

def test_54640():
    with sync_playwright() as p:
        # Step 1: Login user
        browser, context, page = launch_browser(p)
        login_user(page)
        page.wait_for_timeout(2000)

        # Step 2: Reintroduce scenario
        page.get_by_label("Start chat (Floating action)").click()
        page.get_by_label("Start chat", exact=True).click()
        chat_email = "naturesv057+378357867@gmail.com"
        page.get_by_test_id("selection-list-text-input").fill(chat_email)
        page.get_by_label(chat_email).last.click()
        page.get_by_label("Create").last.click() 

        console_errors = []

        # Capture all console messages and filter errors
        def handle_console_msg(msg):
            if msg.type == "error":
                console_errors.append(msg.text)

        page.on("console", handle_console_msg)

        upload_attachment(page)

        # Step 3: Check if the issue is resolved
        failed_load_errors = [error for error in console_errors if "net::ERR_FILE_NOT_FOUND" in error]

        assert not failed_load_errors, f"Test Failed! Error found:\n" + "\n".join(failed_load_errors)

        # Delete created Pdf file
        delete_pdf("sample.pdf")
