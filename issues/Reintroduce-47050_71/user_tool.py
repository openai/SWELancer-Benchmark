import sys, os

from utils.trace_cleaner import trace_cleaner

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import re
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import Page, sync_playwright, expect

SITE_URL = "https://dev.new.expensify.com:8082/"
PRIMARY_EMAIL = "expensifyolddot+1734844472@gmail.com"
FIRST_NAME = "Expenolddot"
LAST_NAME = "1734844472"

SUBMIT_EMAIL = "expensifyolddot@gmail.com"
SUBMIT_FULL_NAME = "EXP OLDDOT"

def login_user(
    page: Page,
    email,
    first_name="Asaad",
    last_name="I",
):
    # Step 1: Open expensify url
    page.goto(SITE_URL)

    try:
        # If the user is not logged in, the email input should be visible
        expect(page.locator('input[type="email"]')).to_be_visible(timeout=3000)
    except:
        # If the user is already logged in, do nothing
        return

    # Step 3: Enter email and click continue
    page.locator('input[type="email"]').fill(email)
    page.locator("button", has_text="Continue").click()

    # Step 4: Click join button
    page.locator("button", has_text="Join").click()

    # Step 5: Select 'Track and budget expenses' in onobarding page and click Continue
    # wait for the text to be visible
    page.locator("text='Track and budget expenses'").wait_for()
    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()

    # Step 6: Enter first name, last name and click continue
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("form").get_by_role("button", name="Continue").click()

    # Step 7: Wait for the onboarding process to complete,
    # this can be crucial to avoid any flakiness in the test
    page.get_by_label("Last chat message preview").filter(
        has_text="task for Track an expense"
    ).click()
    page.get_by_label("guided-setup-track-personal-").wait_for()


def generate_invoice_template(filename):
    """
    Generate an invoice template image
    """
    # Create a blank white image
    width, height = 750, 1000
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)

    # Set up fonts (use a default PIL font)
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except IOError:
        font = ImageFont.load_default()

    # Draw placeholders for the invoice template
    draw.text((20, 20), "Invoice Template", fill="black", font=font)
    draw.text((20, 60), "Company Name: [Your Company]", fill="black", font=font)
    draw.text((20, 100), "Date: [Invoice Date]", fill="black", font=font)
    draw.text((20, 140), "Bill To: [Customer Name]", fill="black", font=font)
    draw.text((20, 180), "Address: [Customer Address]", fill="black", font=font)

    # Draw table headers
    draw.text((20, 240), "Item Description", fill="black", font=font)
    draw.text((400, 240), "Quantity", fill="black", font=font)
    draw.text((520, 240), "Price", fill="black", font=font)
    draw.text((620, 240), "Total", fill="black", font=font)

    # Draw lines to create table structure
    draw.line(
        (20, 270, 730, 270), fill="black", width=2
    )  # Horizontal line below headers
    y = 310
    for i in range(5):  # Draw 5 rows for items
        draw.line((20, y, 730, y), fill="black", width=1)
        y += 40

    img_byte_arr = BytesIO()
    image.save(img_byte_arr, format="PNG")
    img_byte_arr.seek(0)  # Move the pointer to the start of the BytesIO buffer
    return img_byte_arr


def verify_receipt_has_thumbnail_while_uploading(page: Page, email):
    """
    Verify that the receipt has a thumbnail while uploading
    """
    # Step 1: Fill in expense details and submit
    page.get_by_label("Start chat (Floating action)").click()
    page.get_by_label("Submit expense").first.click()
    page.get_by_label("Manual").click()
    page.get_by_placeholder("0").fill("1")
    page.locator("#numPadContainerView").get_by_role("button", name="Next").click()
    page.get_by_test_id("selection-list-text-input").fill(email)
    page.locator(f'button[aria-label="{SUBMIT_FULL_NAME}"]:has(div:has-text("{SUBMIT_FULL_NAME}"))').last.click()
    page.get_by_label("More", exact=True).click()
    page.get_by_label("Add receipt").click()

    # Step 2: Upload a receipt file
    # Generate the invoice template image
    file_name = "invoice-template.png"
    file_object = generate_invoice_template(file_name)

    with page.expect_file_chooser() as fc_info:
        page.get_by_label("Choose file").click()
    file_chooser = fc_info.value
    file_chooser.set_files(
        [
            {
                "name": file_name,  # Set the file name
                "mimeType": "image/png",  # Set the MIME type for PNG
                "buffer": file_object.getvalue(),  # Get the bytes of the in-memory PNG file
            }
        ]
    )

    # Step 3: Click Submit button
    page.get_by_role("button", name=re.compile(r"^Submit")).click()

    # Step 4: Verify that the receipt thumbnail shows the correct image during upload
    # Locate the thumbnail and check if it contains the correct 'src' attribute or style
    parent_locator = page.get_by_label("View details").locator("visible=true").first
    receipt_thumbnail = parent_locator.locator("img")
    receipt_thumbnail.wait_for()
    src_attr = receipt_thumbnail.get_attribute("src")

    # Step 5: Clean up before assertion
    parent_locator.click()
    page.locator(f'button[aria-label*="{SUBMIT_FULL_NAME} owes"]:has(div:has-text("{SUBMIT_FULL_NAME} owes"))').last.click()
    page.get_by_label("Delete expense").click()
    page.get_by_role("button", name="Delete").click()
    parent_locator.wait_for(state="detached")
    # Wait for the chat to load properly in order to avoid flakiness in persistent context
    page.locator("svg[id=fallback-avatar_svg__Layer_1]").first.wait_for(
        state="hidden", timeout=20000
    )

    # Step 6: Assert that the thumbnail has a src attribute with 'blob:'
    assert "blob:" in src_attr, "The Thumbnail did not load in time"


def test_image_thumbnail_should_appear_after_upload():
    """
    Test that the image thumbnail should appear quickly after upload
    """
    with sync_playwright() as playwright:
        # Step 0: Launch browser
        browser = playwright.chromium.launch(
            channel="chrome",
            headless=True,
            args=[
                "--ignore-certificate-errors",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process"
            ],
            proxy={"server": "http://localhost:8080"},
            slow_mo=1000
        )
        context_args = {}
        context_args["timezone_id"] = "Asia/Kathmandu"
        context = browser.new_context(**context_args)

        # Start tracing
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        try:
            page = context.new_page()

            # Step 1: Login user using the utility function
            login_user(page, PRIMARY_EMAIL, FIRST_NAME, LAST_NAME)

            # Step 2: Verify that the receipt has a thumbnail while uploading
            verify_receipt_has_thumbnail_while_uploading(page, SUBMIT_EMAIL)
        except Exception as e:
            raise e
        finally:
            # Stop tracing and export
            context.tracing.stop()
            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            context.tracing.export(trace_path)
            trace_cleaner(trace_path)
            context.close()
            browser.close()
