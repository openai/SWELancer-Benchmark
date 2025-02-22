import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

"""
Tests for the issue: https://github.com/Expensify/App/issues/33740
"""

import logging
import sys
import time

from playwright.sync_api import expect, sync_playwright


EXPENSIFY_URL = "https://dev.new.expensify.com:8082/"


logging.basicConfig(level=logging.INFO, stream=sys.stdout, format="%(message)s")
LOGGER = logging.getLogger(__name__)


EMAILS = [
    'testuser+1733646285@gmail.com',
    'testuser+1733646291@gmail.com',
    'testuser+1733646296@gmail.com',
    'testuser+1733646302@gmail.com',
    'testuser+1733646308@gmail.com'
]

def launch_app(pw, headless=True, device=None, geolocation=None):
    """
    Launch the Expensify app.
    """
    browser = pw.chromium.launch(channel="chrome", headless=True, args=["--disable-web-security",
    "--disable-features=IsolateOrigins,site-per-process"
    ],slow_mo=1000)
    context_args = {}
    if device:
        context_args.update(pw.devices[device])
    if geolocation:
        context_args["geolocation"] = geolocation
        context_args["permissions"] = ["geolocation"]
    context = browser.new_context(**context_args)
    page = context.new_page()
    page.goto(EXPENSIFY_URL)
    return browser, context, page


def login_user(page, email, first_name="John", last_name="Doe"):
    """
    Login to the Expensify app and complete the onboarding.
    """

    page.get_by_test_id("username").fill(email)
    page.get_by_role("button", name="Continue").click()
    page.get_by_role("button", name="Join").click()

    page.get_by_label("Track and budget expenses").click()
    page.get_by_role("textbox", name="First name").fill(first_name)
    page.get_by_role("textbox", name="Last name").fill(last_name)
    page.get_by_role("button", name="Continue").click()


def test_split_expense_tooltip_shows_users_display_name():
    """
    Verify that the Split expense tooltip shows the display name of the users instead of their emails.

    Note: The test is quite resource intensive as it requires simultaneously logging in 5 users. The test might fail
    if enough resources (particularly RAM) are not available.
    """
    with sync_playwright() as pw:

        users = []
        for i, email in enumerate(EMAILS, start=1):
            fname = f"Fname {i}"
            lname = f"Lname {i}"

            headless = i != 1
            browser, context, page = launch_app(pw, headless=headless)
            login_user(page, email, first_name=fname, last_name=lname)
            name = f"{fname} {lname}"
            user_info = {
                "email": email,
                "name": name,
                "browser": browser,
                "context": context,
                "page": page,
            }
            users.append(user_info)
            LOGGER.info("User logged in - Name: %s, Email: %s", name, email)


        page = users[0]["page"]


        page.get_by_label("Start chat (Floating action)").click()
        page.get_by_text("Start chat").click()


        for user in users[1:]:
            page.get_by_test_id("selection-list-text-input").fill(user["email"])
            page.get_by_label(user["name"]).get_by_role("button", name="Add to group").click()


        page.get_by_role("button", name="Next").click()
        page.get_by_role("button", name="Start group").click()


        page.get_by_role("button", name="Create").click()
        page.get_by_text("Split expense").click()
        page.get_by_role("button", name="Manual").click()
        page.locator("input[class='css-textinput-11aywtz r-placeholderTextColor-6taxm2']").fill(str(len(users) * 10))
        page.get_by_role("button", name="Next").click()
        page.get_by_role("button").get_by_text("Split").click()


        page.locator("div[class='css-text-146c3p1']").get_by_text("+").hover()

        page.wait_for_timeout(2000)

        expected_tooltip_text = ", ".join(user["name"] for user in users[3:])
        LOGGER.info("Expected tooltip text: %s", expected_tooltip_text)
        assert_message = f"The tooltip should show '{expected_tooltip_text}'"
        expect(page.get_by_text(expected_tooltip_text), assert_message).to_be_visible(timeout=3)


        for user in users:
            user["context"].close()
            user["browser"].close()
