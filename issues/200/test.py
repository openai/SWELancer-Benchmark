import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect

import random
import time


URL = "https://dev.new.expensify.com:8082/"


def generate_random_email():
    return "freelancer.test.exp+8788@gmail.com"


def login_user(page, email, first_name="Test", last_name="User"):
    page.locator('input[type="email"]').fill(email)
    page.wait_for_timeout(2000)
    page.get_by_role("button", name="Continue").click()    
    page.wait_for_timeout(3000)
    page.evaluate("""
        Onyx.merge('nvp_onboarding', { hasCompletedGuidedSetupFlow: false });
            """)

    page.reload()
    page.wait_for_timeout(1000)
    page.get_by_role("button", name="Join").click()
    page.wait_for_timeout(1000)
    page.locator("text=Track and budget expenses").click()
    page.get_by_role("textbox", name="First name").fill(first_name)
    page.get_by_role("textbox", name="Last name").fill(last_name)
    page.get_by_role("button", name="Continue").click()


def test_expensify_19132():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True, args=[
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process"
            ])
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()        
        email = generate_random_email()
        page.goto(URL)
        login_user(page, email)

        page.wait_for_timeout(1000)
        page.get_by_label("Start chat (Floating action)").click()
        page.get_by_label("Start chat", exact=True).click()
        page.wait_for_timeout(1000)
        page.get_by_test_id("selection-list").get_by_label("Test User (you)").click()
        page.get_by_role("button", name="Create").click()
        page.get_by_label("Assign task").click()
        page.wait_for_timeout(1000)
        page.get_by_role("textbox", name="Title").fill("Task Yourself")
        page.get_by_role("textbox", name="Description (optional)").fill("Task Yourself Description")
        page.wait_for_timeout(1000)
        page.get_by_role("button", name="Next").click()
        page.get_by_role("menuitem", name="Assignee").click()
        page.wait_for_timeout(1000)
        expect(page.get_by_test_id("selection-list").get_by_label("Test User")).to_be_visible()