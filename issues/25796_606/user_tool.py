import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import os
from io import BytesIO
import base64
from io import BytesIO
from playwright.sync_api import sync_playwright, expect
from utils.trace_cleaner import trace_cleaner

first_name = "Sujil"
last_name = "Devkota"
site_url = "https://dev.new.expensify.com:8082/"


# Utility to generate a PDF in memory
def create_in_memory_pdf():
    pdf_base64 = """
JVBERi0xLjMKMyAwIG9iago8PC9UeXBlIC9QYWdlCi9QYXJlbnQgMSAwIFIKL1Jlc291cmNlcyAyIDAgUgovQW5ub3RzIFs8PC9UeXBlIC9Bbm5vdCAvU3VidHlwZSAvTGluayAvUmVjdCBbMjc4LjQ3IDc0OC42NyAzNDUuMTYgNzM2LjY3XSAvQm9yZGVyIFswIDAgMF0gL0EgPDwvUyAvVVJJIC9VUkkgKGh0dHBzOi8vd3d3Lm9wZW5haS5jb20pPj4+Pl0KL0NvbnRlbnRzIDQgMCBSPj4KZW5kb2JqCjQgMCBvYmoKPDwvRmlsdGVyIC9GbGF0ZURlY29kZSAvTGVuZ3RoIDE0OD4+CnN0cmVhbQp4nEWMPQvCMBRF9/6KO+rg8yXavnRUtKAIKgb3QlONH6Vqof58Gy24nOFyz9FYR0yxoI3mFuNMQWlihi2xtGHSWkgMJI1JBLbA4JDf65vDbpGh9c0Z1r0b5FWBja+uQ9hLMB/gLsM91ZfPE0JQDE0FMkmJf8Gjf/kG29pVs1Xv/19CRpAkJIwRU9JVHErsow8m8CxdCmVuZHN0cmVhbQplbmRvYmoKMSAwIG9iago8PC9UeXBlIC9QYWdlcwovS2lkcyBbMyAwIFIgXQovQ291bnQgMQovTWVkaWFCb3ggWzAgMCA1OTUuMjggODQxLjg5XQo+PgplbmRvYmoKNSAwIG9iago8PC9UeXBlIC9Gb250Ci9CYXNlRm9udCAvSGVsdmV0aWNhCi9TdWJ0eXBlIC9UeXBlMQovRW5jb2RpbmcgL1dpbkFuc2lFbmNvZGluZwo+PgplbmRvYmoKMiAwIG9iago8PAovUHJvY1NldCBbL1BERiAvVGV4dCAvSW1hZ2VCIC9JbWFnZUMgL0ltYWdlSV0KL0ZvbnQgPDwKL0YxIDUgMCBSCj4+Ci9YT2JqZWN0IDw8Cj4+Cj4+CmVuZG9iago2IDAgb2JqCjw8Ci9Qcm9kdWNlciAoUHlGUERGIDEuNy4yIGh0dHA6Ly9weWZwZGYuZ29vZ2xlY29kZS5jb20vKQovQ3JlYXRpb25EYXRlIChEOjIwMjQxMjE5MDQ1MDQ3KQo+PgplbmRvYmoKNyAwIG9iago8PAovVHlwZSAvQ2F0YWxvZwovUGFnZXMgMSAwIFIKL09wZW5BY3Rpb24gWzMgMCBSIC9GaXRIIG51bGxdCi9QYWdlTGF5b3V0IC9PbmVDb2x1bW4KPj4KZW5kb2JqCnhyZWYKMCA4CjAwMDAwMDAwMDAgNjU1MzUgZiAKMDAwMDAwMDQ0NCAwMDAwMCBuIAowMDAwMDAwNjI3IDAwMDAwIG4gCjAwMDAwMDAwMDkgMDAwMDAgbiAKMDAwMDAwMDIyNiAwMDAwMCBuIAowMDAwMDAwNTMxIDAwMDAwIG4gCjAwMDAwMDA3MzEgMDAwMDAgbiAKMDAwMDAwMDg0MCAwMDAwMCBuIAp0cmFpbGVyCjw8Ci9TaXplIDgKL1Jvb3QgNyAwIFIKL0luZm8gNiAwIFIKPj4Kc3RhcnR4cmVmCjk0MwolJUVPRgo="""  # shortened for readability
    pdf_bytes = base64.b64decode(pdf_base64)
    return BytesIO(pdf_bytes)


def upload_file_from_memory(page, pdf_bytes_io):
    # Locate and click the "Create" button
    create_button = page.locator("button[aria-label='Create']").locator("visible=true")
    expect(create_button).to_be_visible()
    create_button.click()
    page.wait_for_timeout(1000)

    # Locate the "Add attachment" option and click it
    add_attachment = page.locator("div[aria-label='Add attachment'][role='menuitem']").locator("visible=true").get_by_text("Add attachment")
    with page.expect_file_chooser() as file_chooser_info:
        add_attachment.click()
        page.wait_for_timeout(1000)

    # Use the in-memory PDF directly with `buffer`
    file_chooser = file_chooser_info.value
    file_chooser.set_files([
        {
            "name": "sample.pdf",
            "mimeType": "application/pdf",
            "buffer": pdf_bytes_io.getvalue()
        }
    ])
    print("Uploading in-memory PDF as buffer")
    page.wait_for_timeout(2000)  # Wait for the file to load in preview

    # Press the 'Send' button
    send_button = page.locator("button[aria-label]").locator("visible=true").get_by_text("Send")
    expect(send_button).to_be_visible()
    send_button.click()
    page.wait_for_timeout(4000)  # Wait for the file to upload


# Base function to create an account and log in to Expensify
def create_new_account_and_login(page):
    user_email = "exxppo496s71@gmail.com"
    page.goto(site_url)

    # Create a new account as a random user
    phone_or_email_input = page.locator('input[type="email"]')
    expect(phone_or_email_input).to_be_visible()
    phone_or_email_input.fill(user_email)
    page.wait_for_timeout(1000)

    # Click Continue
    continue_button = page.locator('button[tabindex="0"]')
    expect(continue_button).to_be_visible()
    continue_button.click()
    page.wait_for_timeout(1000)

    # Click join button if it appears
    try:
        print("Clicking the join button again if needed")
        expect(continue_button).to_be_visible()
        continue_button.click()
    except Exception as e:
        pass

    # Select 'Track and budget expenses' on the onboarding page and fill in first and last name
    page.locator("text='Track and budget expenses'").click()
    page.wait_for_timeout(1000)
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()
    page.wait_for_timeout(1000)

    return user_email

# function to upload pdf and verify the mouse hover icon
def test_send_message_and_edit():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, slow_mo=1000, args=["--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"])
        context = browser.new_context()

        # Start tracing
        context.tracing.start(screenshots=True, snapshots=True, sources=True)

        page = context.new_page()

        try:
            # Create an account and log in
            user_email = create_new_account_and_login(page)

            # Step 1: Open personal chat
            personal_chat = page.get_by_text(f"{first_name} {last_name} (you)")
            expect(personal_chat).to_be_visible()
            personal_chat.click()
            page.wait_for_timeout(1000)

            # Step 2: Generate an in-memory PDF and upload it
            pdf_bytes_io = create_in_memory_pdf()
            upload_file_from_memory(page, pdf_bytes_io)

            # Step 3: Get the last message and right click on it
            messages = page.locator('div[aria-label="Chat message"]')
            last_message_index = messages.count() - 1  # As we have sent 1 message
            message = messages.nth(last_message_index)
            expect(message).to_be_visible()
            # Find the button with aria-label "View attachment" inside the last message
            view_attachment_button = message.locator('button[aria-label="View attachment"]')
            expect(view_attachment_button).to_be_visible()
            # Click the "View attachment" button
            view_attachment_button.click()
            page.wait_for_timeout(4000)

            # Test 1: Verify the mouse hover icon is default on the text hover
            pdf_page = page.locator('div[data-page-number="1"]')
            pdf_text_content = pdf_page.locator('.react-pdf__Page__textContent')
            expect(pdf_text_content).to_be_visible()
            pdf_text_content.hover()
            cursor_style_text = pdf_text_content.evaluate('element => getComputedStyle(element).cursor')
            assert cursor_style_text in ['default', 'auto'], f"Expected cursor to be 'default' or 'auto', but got {cursor_style_text}"

            # Test 2: Verify the mouse hover icon is pointer on the link hover
            link_element = pdf_page.locator('.react-pdf__Page__annotations').locator('section').first.locator('a')
            link_element.hover()
            cursor_style_link = link_element.evaluate('element => getComputedStyle(element).cursor')
            assert cursor_style_link == 'pointer', f"Expected cursor to be 'pointer' (hand icon), but got {cursor_style_link}"

        except Exception as e:
            print("Test failed:", e)
            raise e
        finally:
            # Stop tracing and save the trace, then clean it
            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")

            # Close browser in finally block so it always runs
            browser.close()
