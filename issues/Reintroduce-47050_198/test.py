import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import os
import re
import time
from playwright.sync_api import Playwright, Browser, Page, sync_playwright, expect
from PIL import Image, ImageDraw, ImageFont


def login_user(p: Playwright, first_name="D", last_name="C") -> tuple[Browser, Page, str]:
    # Launch chromium and open new page
    browser = p.chromium.launch(
        slow_mo=500,
        headless=True,
        proxy={'server': 'http://127.0.0.1:8080'},
        args=[
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process'
        ],
    )
    page = browser.new_page()
    user_email = 'testuserexpensify+189237@gmail.com'

    # Step 1: Open expensify url
    page.goto('https://dev.new.expensify.com:8082/')

    # Step 2: Enter email and click continue
    page.get_by_test_id("username").fill(user_email)
    page.get_by_role("button", name="Continue").click()

    # Step 3: Click join button
    page.get_by_role("button", name="Join").click()
    expect(page.locator("text=What do you want to do today?")).to_be_visible(timeout=30000)

    # Step 4: Select 'Track and budget expenses' in onboarding page and click Continue
    page.locator("text='Track and budget expenses'").click()

    # Step 5: Enter first name, last name and click continue
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()

    return browser, page, user_email

def generate_invoice_template(filename):
    # Create a blank white image
    width, height = 750, 1000
    image = Image.new('RGB', (width, height), 'white')
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
    draw.line((20, 270, 730, 270), fill="black", width=2)  # Horizontal line below headers
    y = 310
    for i in range(5):  # Draw 5 rows for items
        draw.line((20, y, 730, y), fill="black", width=1)
        y += 40

    # Save the generated image
    image.save(filename)

def test_image():
    with sync_playwright() as playwright:
        # Step 1: Login user using the utility function
        browser, page, user_email = login_user(playwright)

        # Step 2: Fill in expense details and submit
        page.get_by_label("Start chat (Floating action)").click()
        page.get_by_label("Submit expense").click()
        page.get_by_label("Manual").click()
        page.get_by_placeholder("0").fill("1")
        page.locator("#numPadContainerView").get_by_role("button", name="Next").click()
        page.get_by_test_id("selection-list-text-input").fill("a@e.com")
        page.get_by_label("a@e.com").click()
        page.get_by_label("More", exact=True).click()
        page.get_by_label("Add receipt").click()

        # Step 3: Upload a receipt file
        file_path = os.path.expanduser("./invoice-template-us-neat-750px.png")
        # Generate the invoice template image
        generate_invoice_template(file_path)
        # Check if the file exists
        if os.path.exists(file_path):
            with page.expect_file_chooser() as fc_info:
                page.get_by_label("Choose file").click()
            file_chooser = fc_info.value
            file_chooser.set_files(file_path)
        else:
            raise FileNotFoundError(f"File not found: {file_path}")

        # Step 4: Click Submit button
        page.get_by_role("button", name=re.compile(r"^Submit")).click()

        # Step 5: Verify that the receipt thumbnail shows the correct image during upload
        # Locate the thumbnail and check if it contains the correct 'src' attribute or style
        parent_locator = page.get_by_label("View details")
        receipt_thumbnail = parent_locator.locator("div.css-view-175oi2r.r-flexBasis-1mlwlqe img.css-accessibilityImage-9pa8cd")
        # Adding a timeout here because the issue only occurs for a short time; after a delay, usually around 1 second, the thumbnail appears as expected
        expect(receipt_thumbnail).to_have_attribute("src", re.compile(r"blob:"), timeout=500)

        if os.path.exists(file_path):
            os.remove(file_path)

        browser.close()
