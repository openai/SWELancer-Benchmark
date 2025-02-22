import re
import os
import time
import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright, expect

# Expensify app URL
NEWDOT_URL = "https://dev.new.expensify.com:8082"
OLDDOT_URL = "http://127.0.0.1:9000/"
GMAIL = "biruktassew21@gmail.com"

def generate_new_email(email_address=GMAIL):
        # Add random number suffix to the email before the "@" symbol
        username, domain = email_address.split('@')
        timestamp = int(time.time() * 1_000_000)
        return f"{username}+{timestamp}@{domain}"

def signup_user(page, email, first_name="Test", last_name="User"):
    page.get_by_role("textbox", name="Phone or email").fill(email)
    page.get_by_role("button", name="Continue").click()
    page.get_by_role("button", name="Join").click()

    page.wait_for_selector('text="What do you want to do today?"')
    expect(page.locator("text=What do you want to do today?")).to_be_visible()
    
    page.get_by_label("Track and budget expenses").click()
    page.get_by_role("button", name="Continue").click()

    page.fill('input[name="fname"]', first_name)
    page.fill('input[name="lname"]', last_name)
    page.get_by_role("button", name="Continue").last.click()

    page.wait_for_timeout(2000)


def test_new_message_header_font_weight():
    with sync_playwright() as pw:
        
        sender_email_address = "biruktassew21+1739722663455033@gmail.com"
        receiver_email_address = "biruktassew21+1739722663455037@gmail.com"

        # Launch the app
        browser = pw.chromium.launch(
            channel="chrome",
            headless=False,
            args=[
                "--ignore-certificate-errors",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process"
            ],
            proxy={"server": "http://localhost:8080"},
            slow_mo=500
        )
        
        sender_page = browser.new_page()
        receiver_page = browser.new_page()
        sender_page.goto(NEWDOT_URL)
        receiver_page.goto(NEWDOT_URL)
    
        # signup user
        signup_user(sender_page, sender_email_address, first_name="Should Be", last_name="Bold")
        signup_user(receiver_page, receiver_email_address)

        # Send message
        sender_page.get_by_label("Start chat (Floating action)").click()
        sender_page.get_by_text("Start chat").click()
        sender_page.get_by_test_id("selection-list-text-input").fill(receiver_email_address)
        sender_page.get_by_test_id("selection-list").get_by_text(receiver_email_address).last.click()
        sender_page.locator("#composer").fill("Hey there")
        sender_page.keyboard.press('Enter')

        # Check for the message on the receiver side
        receiver_page.locator('button[aria-label="Navigates to a chat"]', has_text="Concierge".replace('"','')).last.click()
        current_url = receiver_page.url
        screen_number = current_url.split("/")[-1]
        receiver_page.get_by_test_id(f"report-screen-{screen_number}").get_by_label("Search").click()

        # Locate the element by text
        element = receiver_page.get_by_text("Should Be Bold").last

        # Extract the computed font-weight style
        font_weight = element.evaluate("el => window.getComputedStyle(el).fontWeight")

        assert(int(font_weight) > 400)
        
        # Close the browser
        browser.close()

