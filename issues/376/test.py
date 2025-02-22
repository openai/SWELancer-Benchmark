import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import io
import tempfile
import pytest
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from reportlab.pdfgen import canvas
from pypdf import PdfReader, PdfWriter
import os



@pytest.fixture(scope="function")
def generate_password_protected_pdf() -> io.BytesIO:
    """
    Generates a password-protected PDF file in memory and returns a BytesIO object.
    
    Returns:
        io.BytesIO: A BytesIO object containing the protected PDF.
    """
    password = "12345"


    pdf_buffer = io.BytesIO()
    c = canvas.Canvas(pdf_buffer)
    c.drawString(100, 750, "This is a password-protected PDF.")
    c.save()


    pdf_buffer.seek(0)


    reader = PdfReader(pdf_buffer)
    writer = PdfWriter()

    for page in reader.pages:
        writer.add_page(page)


    protected_pdf_buffer = io.BytesIO()
    writer.encrypt(user_password=password, use_128bit=True)
    writer.write(protected_pdf_buffer)


    protected_pdf_buffer.seek(0)

    return protected_pdf_buffer

def login_user(p: PlaywrightContextManager, first_name="Milan", last_name="T") -> tuple:
    browser = p.chromium.launch(headless=True, args=[
            '--ignore-certificate-errors',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
        ])
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    user_email = "test25570expensf@gmail.com"


    page.goto('https://dev.new.expensify.com:8082/') 


    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(2000)
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(2000)


    try:

        page.locator('text=What do you want to do today?').wait_for(state='visible', timeout=5000)

        element = page.locator("text='Track and budget expenses'")
        element.scroll_into_view_if_needed()
        element.click()

        page.get_by_role("button", name="Continue").click()


        page.locator('input[name="fname"]').fill(first_name)
        page.locator('input[name="lname"]').fill(last_name)
        page.get_by_role("button", name="Continue").last.click()

        page.wait_for_timeout(2000)
    except TimeoutError:
        pass  # Handle the case when the element is not visible or not found

    return browser, page, context, user_email


def test_PDFPasswordForm_textInput_focus(generate_password_protected_pdf):
    with sync_playwright() as p:

        browser, page, context, user_email = login_user(p)


        protected_file = generate_password_protected_pdf


        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_file.write(protected_file.read())
            temp_file_path = temp_file.name


        page.get_by_label("Start chat (Floating action)").click()
        page.get_by_text("Start chat").click()
        page.get_by_test_id("selection-list").get_by_label("Milan T (you)").click()
        page.get_by_label("Create").last.click()


        with page.expect_file_chooser() as fc_info:

            page.get_by_text("Add attachment").click()


        file_chooser = fc_info.value


        file_chooser.set_files(temp_file_path)


        page.get_by_role("link", name="enter the password").click()
        page.get_by_role("textbox", name="Password").fill("558885558558")
        page.get_by_role("button", name="Confirm").click()


        password_textbox = page.get_by_role("textbox", name="Password")
        expect(password_textbox).to_be_focused(), "Password text input field is not focused"


        os.remove(temp_file_path)


        context.close()
        browser.close()