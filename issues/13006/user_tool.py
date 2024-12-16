import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
import re, time
import os
import imaplib
import email
import re
from PIL import Image, ImageDraw
from io import BytesIO
import random
import string
from utils.trace_cleaner import trace_cleaner

NEWDOT_URL = "https://dev.new.expensify.com:8082/"
OLDDOT_URL = "http://localhost:9000/"
EMAIL = "pehlajrajput1@gmail.com"
PASSWORD = "vjycqezohxxrdhzr"

def new_dot_login(page, email):
    page.goto(NEWDOT_URL)
    page.locator('input[type="email"]').fill(email)
    page.wait_for_timeout(2000)
    page.get_by_role("button", name="Continue").nth(0).click()
    page.wait_for_timeout(10000)
    page.locator('input[data-testid="validateCode"]').fill("123456")

def create_sample_image(width, height, image_format):
    # Create a blank white image
    image = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.text((10, 10), "Sample Image", fill=(0, 0, 0))  # Add some text
    
    img_byte_arr = BytesIO()
    image.save(img_byte_arr, format=image_format)  # Save the image in PNG format
    img_byte_arr.seek(0)
    return img_byte_arr.getvalue()


def profile_picture_fixed(page, format):
    # Navigate to settings
    settings_button = page.get_by_label("My settings")
    expect(settings_button).to_be_visible()
    settings_button.click()
    page.wait_for_timeout(6000)

    # First attempt with large image
    with page.expect_file_chooser() as fc_info:
        page.wait_for_timeout(2000)
        edit_photo = page.get_by_label("Edit photo")
        expect(edit_photo).to_be_visible()
        page.wait_for_timeout(2000)
        edit_photo.click()
        page.get_by_text("Upload photo").click()

    file_chooser = fc_info.value
    page.wait_for_timeout(1000)
    file_chooser.set_files({
        "name": f"test_image.{format.lower()}",
        "mimeType": f"image/{format.lower()}",
        "buffer": create_sample_image(9001, 9000, format)
    })

    # Wait for and verify error message
    error_text = page.get_by_text("Please upload an image larger")
    expect(error_text).to_be_visible(timeout=5000)
    page.wait_for_timeout(2000)

    # Second attempt with correct size
    with page.expect_file_chooser() as fc_info:
        edit_photo = page.get_by_label("Edit photo")
        page.wait_for_timeout(2000)
        expect(edit_photo).to_be_visible()
        page.wait_for_timeout(2000)
        edit_photo.click()
        page.wait_for_timeout(1000)
        page.get_by_text("Upload photo").click()

    file_chooser = fc_info.value
    page.wait_for_timeout(1000)
    file_chooser.set_files({
        "name": f"test_image.{format.lower()}",
        "mimeType": f"image/{format.lower()}",
        "buffer": create_sample_image(250, 250, format)
    })

    # Wait for crop modal and verify elements
    modal = page.get_by_test_id("AvatarCropModal")
    expect(modal).to_be_visible(timeout=5000)
    
    slider = page.get_by_label("slider")
    expect(slider).to_be_visible(timeout=5000)
    
    crop_image = modal.get_by_role("img").nth(1)
    expect(crop_image).to_be_visible(timeout=5000)

    # Get initial state
    initial_bounds = slider.bounding_box()
    if not initial_bounds:
        raise Exception("Could not get slider bounds")

    # Store initial image state
    initial_image_box = crop_image.bounding_box()
    if not initial_image_box:
        raise Exception("Could not get image bounds")

    # Prepare for movement tracking
    image_updates = []
    movement_times = []
    last_update_time = time.time()

    # Perform slider movement with tracking
    slider.hover()
    page.wait_for_timeout(2000)
    page.mouse.down()
    
    target_x = initial_bounds["x"] + 100
    current_x = initial_bounds["x"]
    steps = 10
    step_size = (target_x - current_x) / steps
    
    for i in range(steps):
        step_start_time = time.time()
        
        # Move slider
        page.mouse.move(
            current_x + (step_size * (i + 1)),
            initial_bounds["y"],
            steps=1
        )
        
        # Check for image update
        current_time = time.time()
        image_box = crop_image.bounding_box()
        
        if image_box != initial_image_box:
            update_delay = current_time - step_start_time
            image_updates.append(update_delay)
            movement_times.append(current_time - last_update_time)
            last_update_time = current_time
            initial_image_box = image_box

        page.wait_for_timeout(50)  # Small delay between movements
    
    page.mouse.up()
    
    # Analyze movement and updates
    avg_update_delay = sum(image_updates) / len(image_updates) if image_updates else float('inf')
    max_update_delay = max(image_updates) if image_updates else float('inf')
    update_frequency = len(image_updates) / steps if steps > 0 else 0
    
    print(f"Average image update delay: {avg_update_delay:.3f}s")
    print(f"Maximum image update delay: {max_update_delay:.3f}s")
    print(f"Update frequency: {update_frequency:.2f} updates per step")
    
    # Assert smooth movement criteria
    assert avg_update_delay < 0.2, f"Average image update delay too high: {avg_update_delay:.3f}s"
    assert max_update_delay < 0.5, f"Maximum image update delay too high: {max_update_delay:.3f}s"
    
    # Optional: Click save if available
    save_button = page.get_by_role("button", name="Save")
    if save_button.is_visible():
        save_button.click()
        page.wait_for_timeout(1000)


def test_expensify_0000():
    with sync_playwright() as p:
        browser = p.chromium.launch(proxy = {"server": "http://localhost:8080"}, headless = False, args = ["--no-sandbox", "--disable-dev-shm-usage", "--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"], slow_mo = None, channel = "chromium")
        first_user_context = browser.new_context(ignore_https_errors=True)
        first_user_context.tracing.start(screenshots=True, snapshots=True, sources=True)
        try:
            page = first_user_context.new_page()
            page.wait_for_timeout(2000)
            new_dot_login(page, "pehlajrajput1@gmail.com")
            page.wait_for_timeout(2000)

            profile_picture_fixed(page, 'PNG')
            profile_picture_fixed(page, 'JPEG')
        finally:
            first_user_context.tracing.stop()
            first_user_context.tracing.export_trace("/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            browser.close()
