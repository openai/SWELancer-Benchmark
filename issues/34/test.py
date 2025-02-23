import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import os
import re
import pytest
from PIL import Image, ImageDraw, ImageFont
from playwright.async_api import expect, async_playwright
from utils.login import sign_up, complete_onboarding
from utils.browser import close_browser



async def start_browser(headless=True, proxy=None, launch_args=["--ignore-certificate-errors"]):
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=headless, proxy=proxy, args=launch_args)
    context = await browser.new_context(ignore_https_errors=True)
    page = await context.new_page()
    return context, page, playwright  # Return playwright to close later


def generate_invoice_template(filename):

    width, height = 750, 1000
    image = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(image)


    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except IOError:
        font = ImageFont.load_default()


    draw.text((20, 20), "Invoice Template", fill="black", font=font)
    draw.text((20, 60), "Company Name: [Your Company]", fill="black", font=font)
    draw.text((20, 100), "Date: [Invoice Date]", fill="black", font=font)
    draw.text((20, 140), "Bill To: [Customer Name]", fill="black", font=font)
    draw.text((20, 180), "Address: [Customer Address]", fill="black", font=font)


    draw.text((20, 240), "Item Description", fill="black", font=font)
    draw.text((400, 240), "Quantity", fill="black", font=font)
    draw.text((520, 240), "Price", fill="black", font=font)
    draw.text((620, 240), "Total", fill="black", font=font)


    draw.line((20, 270, 730, 270), fill="black", width=2)  # Horizontal line below headers
    y = 310
    for i in range(5):  # Draw 5 rows for items
        draw.line((20, y, 730, y), fill="black", width=1)
        y += 40


    image.save(filename)



@pytest.mark.asyncio
async def test_image():
    derived_email = "testuserexpensify+15443388@gmail.com"


    context, page, playwright = await start_browser(
        proxy={'server': 'http://127.0.0.1:8080'},
        launch_args=[
        '--disable-web-security',
        '--disable-features=IsolateOrigins,site-per-process'
    ])


    await sign_up(page, derived_email)


    try:
        await complete_onboarding(page)
    except Exception:
        pass


    await expect(page.get_by_label("Inbox")).to_be_visible()


    await page.get_by_label("Start chat (Floating action)").click()
    await page.get_by_label("Submit expense").click()
    await page.get_by_label("Manual").click()
    await page.get_by_placeholder("0").fill("1")
    await page.locator("#numPadContainerView").get_by_role("button", name="Next").click()
    await page.get_by_test_id("selection-list-text-input").fill("a@e.com")
    await page.get_by_label("a@e.com").click()
    await page.get_by_label("More", exact=True).click()
    await page.get_by_label("Add receipt").click()


    file_path = os.path.expanduser("./invoice-template-us-neat-750px.png")

    generate_invoice_template(file_path)

    if os.path.exists(file_path):
        async with page.expect_file_chooser() as fc_info:
            await page.get_by_label("Choose file").click()
        file_chooser = await fc_info.value
        await file_chooser.set_files(file_path)
    else:
        raise FileNotFoundError(f"File not found: {file_path}")


    await page.get_by_role("button", name=re.compile(r"^Submit")).click()



    parent_locator = page.get_by_label("View details")
    receipt_thumbnail = parent_locator.locator("div.css-view-175oi2r.r-flexBasis-1mlwlqe img.css-accessibilityImage-9pa8cd")

    await expect(receipt_thumbnail).to_have_attribute("src", re.compile(r"blob:"), timeout=500)

    if os.path.exists(file_path):
        os.remove(file_path)


    await close_browser(context, page, playwright)
