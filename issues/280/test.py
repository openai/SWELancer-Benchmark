import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
from playwright.sync_api import sync_playwright, expect
from playwright._impl._page import Page 
from io import BytesIO
import zlib
import struct

static_email = "testuserexpensify1+43@gmail.com"

def generate_email(user_name = 'expensify66', domain = 'gmail.com'):
    """
    Generate an email with a timestamp
    """
    timestamp = int(time.time())
    return f"{user_name}+{timestamp}@{domain}"

def choose_link_if_any(page, link_text, retries = 1):
    for _ in range(retries):
        link = page.locator(f'text={link_text}')
        if link.count() == 0:
            page.wait_for_timeout(1000)
        else:
            break

    if link.count() == 0:
        return 

    link.first.click()

def create_png_in_memory():
    """
    Create a basic PNG file in memory using inbuilt modules
    """
    width, height = 100, 100
    bit_depth = 8
    color_type = 2  # Truecolor


    png_signature = b'\x89PNG\r\n\x1a\n'


    ihdr_data = struct.pack(">IIBBBBB", width, height, bit_depth, color_type, 0, 0, 0)
    ihdr = b'IHDR' + ihdr_data
    ihdr_crc = struct.pack(">I", zlib.crc32(ihdr))
    ihdr_chunk = struct.pack(">I", len(ihdr_data)) + ihdr + ihdr_crc


    raw_image_data = b'\x00' + b'\xff\x00\x00' * width  # Red row of 100 pixels
    compressed_data = zlib.compress(raw_image_data * height)
    idat = b'IDAT' + compressed_data
    idat_crc = struct.pack(">I", zlib.crc32(idat))
    idat_chunk = struct.pack(">I", len(compressed_data)) + idat + idat_crc


    iend = b'IEND'
    iend_crc = struct.pack(">I", zlib.crc32(iend))
    iend_chunk = struct.pack(">I", 0) + iend + iend_crc


    png_data = png_signature + ihdr_chunk + idat_chunk + iend_chunk

    return png_data

def verify_unknown_user_profile_load_offline(page: Page, file_name = "Receipt.png"):
    """
    Verify that the unknown user profile page loads offline
    """
    if page.locator("#overLayBottomButton").count() > 0:
        page.locator("#overLayBottomButton").first.click()
    

    unknown_email = generate_email(user_name="testuser")
    file_object = BytesIO(create_png_in_memory())


    page.get_by_label("My settings").click()
    page.get_by_label("Troubleshoot").click()
    force_locator = page.get_by_label("Force offline")
    if force_locator.get_attribute("aria-checked") == "false":
        force_locator.click()


    page.get_by_label("Start chat (Floating action)").click()
    page.get_by_label("Split expense").click()
    page.get_by_label("Scan").click()


    with page.expect_file_chooser() as fc_info:

        page.get_by_label("Choose file").click()
    

    file_chooser = fc_info.value
    file_chooser.set_files([{
        'name': file_name,  # Set the file name
        'mimeType': 'image/png',  # Set the MIME type for PNG
        'buffer': file_object.getvalue()  # Get the bytes of the in-memory PNG file
    }])

    page.get_by_test_id("selection-list-text-input").fill(unknown_email)
    page.get_by_label(unknown_email).first.click()
    page.get_by_role("button", name="Next").click()
    email_locator = page.get_by_test_id("IOURequestStepConfirmation").get_by_label(unknown_email)
    email_locator.first.click()





    try: # the profile loading indicator appeared
        page.get_by_role("progressbar").get_by_role("img").wait_for(timeout=5000)
    except:

        pass
    expect(page.get_by_role("progressbar").get_by_role("img")).to_have_count(0)


def test_unknown_user_profile_load_offline():
    """
    Test that the unknown user profile page loads offline
    """

    site_url = 'https://dev.new.expensify.com:8082/'
    timestamp = int(time.time())
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, slow_mo=1000, args=["--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"])
        page = browser.new_page()

        page.goto(site_url) 

        phone_or_email_input = page.locator('input[type="email"]')

        phone_or_email_input.fill(static_email)

        page.wait_for_timeout(1000)

        continue_button = page.locator('button[tabindex="0"]')

        continue_button.click()
        page.wait_for_timeout(1000)

        try: 
            print("Maybe we need to click again")
            continue_button = page.locator('button[tabindex="0"]')

            continue_button.click()
        except Exception as e:
            pass
        page.wait_for_timeout(5000)



        page.locator("text='Track and budget expenses'").wait_for()
        page.locator("text='Track and budget expenses'").click()
        page.get_by_role("button", name="Continue").click()


        page.locator('input[name="fname"]').fill("Account")
        page.locator('input[name="lname"]').fill(f"{timestamp}")
        page.get_by_role("button", name="Continue").last.click()
        page.wait_for_timeout(1000) 
        choose_link_if_any(page, "Get started")

        page.get_by_label('Last chat message preview').filter(has_text='task for Track an expense').click()
        page.wait_for_timeout(1000) 


        verify_unknown_user_profile_load_offline(page)


        browser.close()

