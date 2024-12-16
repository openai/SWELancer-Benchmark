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
from utils.trace_cleaner import trace_cleaner  # Newly added
import os


# Utility to generate a password protected PDF file in memory
@pytest.fixture(scope="function")
def generate_password_protected_pdf() -> io.BytesIO:
    """
    Generates a password-protected PDF file in memory and returns a BytesIO object.
    
    Returns:
        io.BytesIO: A BytesIO object containing the protected PDF.
    """
    password = "12345"

    # Create a simple PDF in memory
    pdf_buffer = io.BytesIO()
    c = canvas.Canvas(pdf_buffer)
    c.drawString(100, 750, "This is a password-protected PDF.")
    c.save()

    # Move the buffer's cursor to the beginning for reading
    pdf_buffer.seek(0)

    # Read the PDF and encrypt it
    reader = PdfReader(pdf_buffer)
    writer = PdfWriter()

    for page in reader.pages:
        writer.add_page(page)

    # Create a new buffer for the encrypted PDF
    protected_pdf_buffer = io.BytesIO()
    writer.encrypt(user_password=password, use_128bit=True)
    writer.write(protected_pdf_buffer)

    # Move the buffer's cursor to the beginning for reading
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

    # Step 1: Open expensify url
    page.goto('https://dev.new.expensify.com:8082/') 

    # Step 2: Enter email and click continue
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(2000)
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(2000)

    # Step 3: Click join button
    try:
        # Wait explicitly for the element to appear
        page.locator('text=What do you want to do today?').wait_for(state='visible', timeout=5000)
        # Only proceed if the element is visible
        element = page.locator("text='Track and budget expenses'")
        element.scroll_into_view_if_needed()
        element.click()

        page.get_by_role("button", name="Continue").click()

        # Enter first name and last name
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
        # Start tracing
        context.tracing.start(
            title="test_PDFPasswordForm_textInput_focus",
            screenshots=True,
            snapshots=True,
            sources=True
        )
        
        try:
            # Step 2: Use the fixture to get the protected PDF file
            protected_file = generate_password_protected_pdf

            # Save the BytesIO buffer to a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                temp_file.write(protected_file.read())
                temp_file_path = temp_file.name

            # Step 3: Send password protected pdf in a chat.
            page.get_by_label("Start chat (Floating action)").click()
            page.get_by_text("Start chat").click()
            page.get_by_test_id("selection-list").get_by_label("Milan T (you)").click()
            page.get_by_label("Create").last.click()

            # Expect the file chooser to trigger
            with page.expect_file_chooser() as fc_info:
                # Click the "Add Attachment" button that triggers the file chooser dialog
                page.get_by_text("Add attachment").click()

            # Get the file chooser object from the file chooser event
            file_chooser = fc_info.value
            file_chooser.set_files(temp_file_path)

            # Step 3: Go to enter file password and enter wrong password and confirm.
            page.get_by_role("link", name="enter the password").click()
            page.get_by_role("textbox", name="Password").fill("558885558558")
            page.get_by_role("button", name="Confirm").click()

            # Step 4: Verify that focus remains on password input text field.
            password_textbox = page.get_by_role("textbox", name="Password")
            expect(password_textbox).to_be_focused(), "Password text input field is not focused"

            # Clean up the temporary file
            os.remove(temp_file_path)
        except Exception:
            raise
        finally:
            # Stop and save the trace
            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            context.tracing.stop(path=trace_path)
            # Clean the trace
            trace_cleaner(trace_path)

            # Close context and browser
            context.close()
            browser.close()
