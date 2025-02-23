import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
import re, time
import os
import imaplib
import email
import re
import random
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
NEWDOT_URL = "https://dev.new.expensify.com:8082/"
OLDDOT_URL = "http://localhost:9000/"
EMAIL = "pehlajrajput1+89@gmail.com"
PASSWORD = "vjycqezohxxrdhzr"

def new_dot_login(page, email):
    page.goto(NEWDOT_URL)
    page.locator('input[type="email"]').fill(email)
    page.wait_for_timeout(2000)
    page.get_by_role("button", name="Continue").nth(0).click()
    page.wait_for_timeout(10000)
    page.locator('input[data-testid="validateCode"]').fill("123456")

from reportlab.pdfgen import canvas

def create_sample_pdf():

    pdf_byte_arr = BytesIO()


    c = canvas.Canvas(pdf_byte_arr, pagesize=letter)


    c.drawString(100, 750, "Sample PDF")  # Coordinates (x, y) for the text
    c.drawString(100, 730, "This is a sample PDF file generated in Python.")
    

    c.showPage()
    c.save()


    pdf_byte_arr.seek(0)
    return pdf_byte_arr.getvalue()


def attachemet_issue(page):
    format = "pdf"  # Add a default format
    page.get_by_label("Start chat (Floating action)").click()
    page.wait_for_timeout(1000)
    page.get_by_label("Start chat", exact=True).click()
    page.wait_for_timeout(1000)
    page.get_by_test_id("selection-list-text-input").click()
    page.wait_for_timeout(1000)
    page.get_by_test_id("selection-list-text-input").fill("tosomenewuser@gmail.com")
    page.wait_for_timeout(1000)
    page.get_by_label("tosomenewuser@gmail.com").click()
    page.wait_for_timeout(2000)
    current_url = page.url


    match = re.search(r"/r/(\d+)", current_url)
    if match:
        last_id = match.group(1)
        print(f"Extracted last ID: {last_id}")
        

        test_id = f"report-screen-{last_id}"
        page.wait_for_timeout(1000)
    else:
        print("No matching ID found in the URL.")
    page.wait_for_timeout(4000)
    with page.expect_file_chooser() as fc_info:
        page.wait_for_timeout(2000)
        page.get_by_test_id(test_id).get_by_label("Create").click()
        page.wait_for_timeout(1000)
        page.get_by_text("Add attachment").click()
    
    file_chooser = fc_info.value
    page.wait_for_timeout(1000)
    file_chooser.set_files({
        "name": f"test_pdf.{format.lower()}",           
        "mimeType": f"pdf/{format.lower()}",           
        "buffer": create_sample_pdf()    
    })
    page.wait_for_timeout(1000)
    page.get_by_role("dialog").get_by_role("button", name="Send").click()

    assertion_1 =expect(page.get_by_text("Uh-oh, something went wrong!")).not_to_be_visible()
    if assertion_1 == False:
        page.wait_for_timeout(1000)
        page.get_by_role("button", name="Sign out").click()
    else: 
        page.get_by_label("My settings").click()
        page.get_by_label("Sign out").click()
        page.wait_for_timeout(2000)
    
    page.wait_for_timeout(2000)
    new_dot_login(page, "pehlajrajput1+89@gmail.com")
    page.get_by_label("Start chat (Floating action)").click()
    page.wait_for_timeout(1000)
    page.get_by_label("Start chat", exact=True).click()
    page.wait_for_timeout(1000)
    page.get_by_test_id("selection-list-text-input").click()
    page.wait_for_timeout(1000)
    page.get_by_test_id("selection-list-text-input").fill("tosomenewuser@gmail.com")
    page.wait_for_timeout(1000)
    page.get_by_label("tosomenewuser@gmail.com").click()
    page.wait_for_timeout(1000)
    page.get_by_test_id("report-screen-2023706297795678").get_by_label("View attachment").last.click()
    page.wait_for_timeout(1000)
    expect(page.get_by_text("Uh-oh, something went wrong!")).not_to_be_visible()


def test_expensify_0000():
     with sync_playwright() as p:
        browser = p.chromium.launch(proxy = {"server": "http://localhost:8080"}, headless = False, args = ["--no-sandbox", "--disable-dev-shm-usage", "--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"], slow_mo = None, channel = "chromium")        
        first_user_context = browser.new_context(ignore_https_errors=True)
        page = first_user_context.new_page()
        page.wait_for_timeout(2000)
        new_dot_login(page, "pehlajrajput1+89@gmail.com")
        page.wait_for_timeout(2000)

        attachemet_issue(page)

        browser.close()