import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import os
import re

from playwright.sync_api import Playwright, Browser, Page, sync_playwright, expect
from PIL import Image, ImageDraw, ImageFont

# Utility to generate a random email
def generate_random_email():
    
    return 'test+1734080901@gmail.com'

def login_user(p: Playwright, first_name="D", last_name="C") -> tuple[Browser, Page, str]:
    # Launch chromium and open new page
    context_args = {}
    context_args["timezone_id"] = "Asia/Calcutta"
    browser = p.chromium.launch(channel="chrome", headless=True, args=["--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"], slow_mo=1000)
    page = browser.new_page()
    user_email = generate_random_email()

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
    from utils.trace_cleaner import trace_cleaner
    with sync_playwright() as playwright:
        # Step 1: Login user using the utility function
        browser, page, user_email = login_user(playwright)
        page.context.tracing.start(screenshots=True, snapshots=True, sources=True)
        try:
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
            parent_locator = page.get_by_label("View details")
            receipt_thumbnail = parent_locator.locator("div.css-view-175oi2r.r-flexBasis-1mlwlqe img.css-accessibilityImage-9pa8cd")
            expect(receipt_thumbnail).to_have_attribute("src", re.compile(r"blob:"), timeout=500)
        except Exception as e:
            raise e
        finally:
            page.context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            browser.close()
