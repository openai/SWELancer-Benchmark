import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page
from enum import Enum
from PIL import Image
import requests
from io import BytesIO
import platform
import subprocess
import tempfile

# Import the trace cleaner right before using it.
# (We will call it in the finally block after exporting the trace.)

#### CONFIG

TEST_URL = "https://dev.new.expensify.com:8082/" # TODO Use the URL that works in your local development.
# TEST_URL = "https://localhost:8082/" # TODO Use the URL that works in your local development.

USER_NAME = "expensify31" # TODO Change this to your Gmail username
USER_PASSWORD = "Pass@123456" # TODO Change this to your password

#### UTILS

class TodayOptions(Enum):
    TRACK_AND_BUDGET_EXPENSES = 1
    SOMETHING_ELSE = 4


def copy_image_to_clipboard(image_url):
    # Fetch the image from a URL
    response = requests.get(image_url)
    if response.status_code == 200:
        # Open image using Pillow
        image = Image.open(BytesIO(response.content))
        
        # Create a temporary file for the image
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_image_file:
            image_path = temp_image_file.name
            image.save(image_path, "PNG")

        # Platform-specific clipboard copy
        if platform.system() == "Windows":
            # Use PowerShell command to copy image to clipboard
            subprocess.run(f'powershell -command "Add-Type -AssemblyName System.Windows.Forms; ' \
                           f'[System.Windows.Forms.Clipboard]::SetImage([System.Drawing.Image]::FromFile(\'{image_path}\'))"',
                           shell=True)
        elif platform.system() == "Darwin":
            # macOS: Use `osascript` to copy image to clipboard
            subprocess.run(f"osascript -e 'set the clipboard to (read (POSIX file \"{image_path}\") as JPEG picture)'", shell=True)
        else:
            # Linux: Use `xclip` to copy image to clipboard
            subprocess.run(f"xclip -selection clipboard -t image/png -i {image_path}", shell=True)
    else:
        raise Exception(f"Failed to fetch image from URL: {image_url}")


def get_test_user_info(seed = None):
    """
    Get test user info using the seed:
    - If `seed` is None, this function will return a fixed email and name.
    - If `seed` is the `True` boolean value, this function will generate a random number based on the current timestamp and use it as the seed to return a random email and name.
    - Otherwise, this function will return a derivative of the fixed email and corresponding name.
    """
    if seed is None:
        return {"email": f"{USER_NAME}@gmail.com", "password": USER_PASSWORD, "first_name": f"{USER_NAME}", "last_name": "Test"}
    
    if type(seed) == type(True):
        seed = int(time.time())

    return {"email": f"{USER_NAME}+{seed}@gmail.com", "password": USER_PASSWORD, "first_name": f"Test", "last_name": "User"}


def wait(page, for_seconds=1):
    page.wait_for_timeout(for_seconds * 1000)


def choose_what_to_do_today_if_any(page, option: TodayOptions, retries = 5, **kwargs):
    wait(page)

    for _ in range(retries):
        wdyw = page.locator("text=What do you want to do today?")
        if wdyw.count() == 0:
            print('"What do you want to do today?" dialog is not found. Wait and retry...')
            wait(page)
        else:
            break

    if wdyw.count() == 0:
        print('"What do you want to do today?" dialog is not found.')
        return 
    
    expect(wdyw).to_be_visible()
        
    if option == TodayOptions.SOMETHING_ELSE:
        text = "Something else"
    elif option == TodayOptions.TRACK_AND_BUDGET_EXPENSES:
        text='Track and budget expenses'

    page.locator(f"text='{text}'").click()
    page.get_by_role("button", name="Continue").click()

    # Enter first name, last name and click continue
    wait(page)
    page.locator('input[name="fname"]').fill(kwargs['first_name'])
    page.locator('input[name="lname"]').fill(kwargs['last_name'])
    page.get_by_role("button", name="Continue").last.click()


def choose_link_if_any(page, link_text, retries = 5):
    wait(page)

    for _ in range(retries):
        link = page.locator(f'text={link_text}')
        if link.count() == 0:
            print(f'"{link_text}" link is not found. Wait and retry...')
            wait(page)
        else:
            break

    if link.count() == 0:
        print(f'"{link_text}" link is not found.')
        return 
    
    expect(link).to_be_visible()
    link.click()


def login(p: PlaywrightContextManager, user_info, if_phone=False) -> tuple[Browser, Page]:    

    permissions = ['clipboard-read', 'clipboard-write']
    browser = p.chromium.launch(channel="chrome", headless=True, slow_mo = 500, args=[
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ])

    if if_phone:
        phone = p.devices['iPhone 12 Pro']
        context = browser.new_context(**phone, permissions=permissions, reduced_motion='no-preference')
    else:
        context = browser.new_context()

    page = context.new_page()

    page.goto(TEST_URL, timeout=120000) # Timeout is set to 120 seconds

    phone_or_email_input = page.locator('input[type="email"]')
    expect(phone_or_email_input).to_be_visible()
    phone_or_email_input.fill(user_info["email"])

    continue_button = page.locator('button[tabindex="0"]')
    expect(continue_button).to_be_visible()
    continue_button.click()

    # Step 2: Click Join button if the user is new. Or, use Magic Code to sign in if the user is existing.
    wait(page)

    join_button = page.locator('button:has-text("Join")')
    if join_button.count() > 0:
        print("Join button found. This is a new user.")
        join_button.click()
    else:
        validate_code_input = page.locator('input[data-testid="validateCode"]')
        expect(validate_code_input).to_be_visible()
        validate_code_input.fill("564736")

    return browser, page

#### TESTS

def test():
    with sync_playwright() as p:
        # We'll store references so we can close them or export traces in finally.
        trace_path = "/app/expensify/user_tool/output_browser1.zip"
        context = None
        browser = None
        try:
            # Step 1: Login
            user_info = get_test_user_info(seed=6)
            browser, page = login(p, user_info, False)

            # Grab the context so we can record traces.
            context = page.context
            context.tracing.start(screenshots=True, snapshots=True, sources=True)

            # The rest of the test steps
            page.get_by_label("Start chat (Floating action)").click()
            page.get_by_text("Start chat").click()
            random_integer = int(time.time())
            page.get_by_test_id("selection-list-text-input").fill(f"otheritems{random_integer}@gmail.com")
            page.get_by_label(f"otheritems{random_integer}@gmail.com").click()
            page.get_by_label("Create").nth(1).click()
            page.get_by_text("Assign task").click()
            page.get_by_role("textbox", name="Title").click()
            page.get_by_role("textbox", name="Title").fill("TestingUser")
            page.get_by_role("button", name="Next").click()
            page.get_by_text("Assignee").click()
            page.get_by_test_id("selection-list-text-input").fill("+919087740628")
            page.get_by_label("40628").click()
            page.get_by_role("button", name="Confirm task").click()
            page.wait_for_timeout(2000)
            element = page.get_by_text("There was an error creating")
            expect(element).not_to_be_visible(timeout=100)
        except Exception as e:
            # If there's an error, we'll re-raise it after stopping trace.
            raise e
        finally:
            # Always stop and export trace, then clean it.
            if context:
                context.tracing.stop()
                context.tracing.export(trace_path)
                from utils.trace_cleaner import trace_cleaner
                trace_cleaner(trace_path)
            if browser:
                browser.close()
