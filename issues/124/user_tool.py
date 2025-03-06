import os
from playwright.sync_api import sync_playwright, expect
from utils.trace_cleaner import trace_cleaner


# Expensify app URL
EXPENSIFY_URL = "https://dev.new.expensify.com:8082/"

# Email login credentials
EMAIL_USERNAME = "naturesv057+52319_4@gmail.com"

def launch_browser(pw, device=None, geolocation=None):
    """
    Launch the browser.
    """
    browser = pw.chromium.launch(
        headless=False,
        proxy={"server": "http://127.0.0.1:8080/"},
        args=[
            "--ignore-certificate-errors",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
        ],
        slow_mo=500
    )
    context_args = {}
    if device:
        context_args.update(pw.devices[device])
    if geolocation:
        context_args["geolocation"] = geolocation
        context_args["permissions"] = ["geolocation"]
    context = browser.new_context(**context_args)
    page = context.new_page()
    return browser, context, page


def login_user(page):
    """
    Login to the Expensify app and complete the onboarding.
    """
    # Open the Expensify app
    page.goto(EXPENSIFY_URL)

    # Login user
    page.get_by_role("textbox", name="Phone or email").fill(EMAIL_USERNAME)
    page.locator("div", has_text="Continue").last.click()
    
    # Get the OTP code from the email
    otp = "123456"
    
    # Enter the OTP code
    page.keyboard.type(otp)


def upload_attachment(page):
    filename = "output.txt"

    with open(filename, "wb") as file:
        for i in range(1, 101):
            line = f"Line {i}: This is a sample line of content.\n"
            file.write(line.encode("utf-8"))  # Convert string to bytes

    edit_text_button = page.locator('div[aria-label="Add attachment"]').locator("visible=true")
    
    with page.expect_file_chooser() as file_chooser_info:
        edit_text_button.click()
    page.wait_for_timeout(3000)
    file_chooser = file_chooser_info.value
    file_path = os.path.join(os.getcwd(), filename)
    file_chooser.set_files(file_path)
    page.wait_for_timeout(2000)

    page.locator('button:has-text("Send")').click()
    page.wait_for_timeout(2000) 
    return page


def test_52319():
    with sync_playwright() as p:
        browser, context, page = launch_browser(p)
        # Start tracing
        context.tracing.start(screenshots=True, snapshots=True, sources=True)

        try:
            # Step 1: Login user
            login_user(page)
            page.wait_for_timeout(2000)

            # Step 2: Reintroduce scenario
            page.get_by_label("Start chat (Floating action)").click()
            page.get_by_label("Start chat", exact=True).click()
            chat_email = "naturesv057+378357843@gmail.com"
            page.get_by_test_id("selection-list-text-input").fill(chat_email)
            page.get_by_label(chat_email).last.click()
            page.locator("#composer").last.fill("Hi There")
            page.get_by_label("Create").last.click() 

            page = upload_attachment(page)

            #Step 3: Check if the issue is resolved
            page.locator("#composer").last.click()
            page.locator("#composer").last.press("ArrowUp")
            expect(page.get_by_role("button", name="Save changes")).to_be_visible()
        finally:
            # Stop tracing and export trace file
            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            context.tracing.stop(path=trace_path)
            trace_cleaner(trace_path)
            browser.close()


if __name__ == "__main__":
    test_52319()
