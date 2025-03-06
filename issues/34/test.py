from playwright.sync_api import sync_playwright, expect
import re
import os
import struct
import random
import binascii


user_email = "totherandomuser+54226@gmail.com"


def login(p, context):
    page = context.new_page()
    page.goto('https://dev.new.expensify.com:8082')

    # Step 1: Enter username and continue
    page.get_by_test_id("username").click()
    page.get_by_test_id("username").fill(user_email)
    page.get_by_role("button", name="Continue").click()

    # Step 2: Mark Inbox read and then get magic code from email
    magic_code = "123456"

    # Step 3: Fill in the magic code
    validate_code_input = page.locator('input[name="validateCode"]')
    expect(validate_code_input).to_be_visible()
    validate_code_input.fill(magic_code)
    page.wait_for_timeout(1000)

    return page


def generate_valid_png(filename="dummy_image.png", size_mb=30):
    """Generates a valid 30MB PNG file without using external packages."""

    target_size = size_mb * 1024 * 1024  # Convert MB to bytes

    # PNG Signature (Required for a valid PNG)
    png_signature = b'\x89PNG\r\n\x1a\n'

    width, height = 100, 100  # Small placeholder image
    bit_depth, color_type, compression, filter_method, interlace = 8, 2, 0, 0, 0
    ihdr_data = struct.pack(">IIBBBBB", width, height, bit_depth, color_type, compression, filter_method, interlace)

    ihdr_chunk = struct.pack(">I", len(ihdr_data)) + b'IHDR' + ihdr_data
    ihdr_chunk += struct.pack(">I", binascii.crc32(b'IHDR' + ihdr_data) & 0xFFFFFFFF)

    idat_size = target_size - (len(png_signature) + len(ihdr_chunk) + 12)  # Leave space for other chunks
    idat_data = bytes(random.getrandbits(8) for _ in range(idat_size))

    idat_chunk = struct.pack(">I", len(idat_data)) + b'IDAT' + idat_data
    idat_chunk += struct.pack(">I", binascii.crc32(b'IDAT' + idat_data) & 0xFFFFFFFF)

    iend_chunk = struct.pack(">I", 0) + b'IEND'
    iend_chunk += struct.pack(">I", binascii.crc32(b'IEND') & 0xFFFFFFFF)

    with open(filename, "wb") as f:
        f.write(png_signature)  # PNG Signature
        f.write(ihdr_chunk)     # IHDR Chunk
        f.write(idat_chunk)     # IDAT Chunk (Random data for size)
        f.write(iend_chunk)     # IEND Chunk

    print(f"Valid PNG file created: {filename} ({os.path.getsize(filename) / (1024 * 1024):.2f} MB)")


def test():
    with sync_playwright() as p:

        # Step 1: Main Browser Login
        browser = p.chromium.launch(headless=False, args=[
                        "--disable-web-security",
                        "--disable-features=IsolateOrigins,site-per-process"],
                        slow_mo=500)
        
        context = browser.new_context()
        page = login(p, context)

        try:

            # Generate a valid 30MB PNG file
            generate_valid_png()
            image_path = "dummy_image.png"

            # Upload attachment in a group and check the message.
            page.get_by_test_id("6349439519205822").click()
            page.get_by_test_id("report-screen-6349439519205822").get_by_label("Create").click()
            
            with page.expect_file_chooser() as fc_info:
                page.get_by_label("Add attachment").click()
            
            file_chooser = fc_info.value
            file_chooser.set_files(image_path)
            
            # check the message.
            expect(page.get_by_text("Attachment is too largeAttachment size is larger than 24 MB limit")).to_be_visible()
            page.get_by_role("button", name="Close").click()

            # Upload profile picture and check the error message
            page.get_by_label("My settings").click()
            page.get_by_role("menuitem", name="Profile").click()
            with page.expect_file_chooser() as fc_info:
                page.get_by_label("Edit photo").click()

            file_chooser = fc_info.value
            file_chooser.set_files(image_path)

            expect(page.locator("div").filter(has_text=re.compile(r"^The selected image exceeds the maximum upload size of 6 MB\.$")).first).to_be_visible()

            if os.path.exists(image_path):
                os.remove(image_path)

        except Exception as e:
            if os.path.exists(image_path):
                os.remove(image_path)
            raise e