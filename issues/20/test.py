import os, requests
from playwright.sync_api import sync_playwright


# Expensify app URL
EXPENSIFY_URL = "https://dev.new.expensify.com:8082/"

# Email login credentials
EMAIL_USERNAME = "naturesv057+54772_1@gmail.com"

def launch_browser(pw, device=None, geolocation=None):
    """
    Launch the browser.
    """
    browser = pw.chromium.launch(
        headless=False,
        proxy = {"server": "http://127.0.0.1:8080/"},
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


def download_random_image(save_path):
    # URL of a random image
    url = "https://picsum.photos/200/300"
    response = requests.get(url)
    if response.status_code == 200:
        with open(save_path, 'wb') as file:
            file.write(response.content)
        print(f"Image downloaded and saved to {save_path}")
    else:
        print("Failed to download image")


def upload_image_reciept(page, filename):
    download_random_image(filename)
    edit_text_button = page.get_by_label("Choose file")
    
    with page.expect_file_chooser() as file_chooser_info:
        edit_text_button.click()
    page.wait_for_timeout(3000)
    file_chooser = file_chooser_info.value
    file_path = os.path.join(os.getcwd(), filename)
    file_chooser.set_files(file_path)
    page.wait_for_timeout(2000)
    return page

def delete_file(filename):
    """
    Deletes a file in the current working directory.
    
    Args:
    - filename (str): The name of the PDF file to be deleted.
    
    Returns:
    - bool: True if the file was successfully deleted, False if the file does not exist.
    """
    file_path = os.path.join(os.getcwd(), filename)
    
    if os.path.exists(file_path):
        os.remove(file_path)
        return True
    else:
        print(f"File not found, could not delete: {file_path}")
        return False
    
def get_flex_property(page, selector):
    flex_property = page.evaluate('''(selector) => {
        const element = document.querySelector(selector);
        const styles = window.getComputedStyle(element);
        return styles.getPropertyValue('flex');
    }''', selector)
    return flex_property

def test_54772():
    with sync_playwright() as p:
        # Step 1: Login user
        browser, context, page = launch_browser(p)
        login_user(page)
        page.wait_for_timeout(2000)

        # Step 2: Reintroduce scenario
        page.get_by_label("Start chat (Floating action)").click()
        page.get_by_test_id("PopoverMenuItem-Create expense").click()

        # Path to save the downloaded image
        filename = "test_image.tiff"
        page = upload_image_reciept(page, filename)
        
        page.get_by_test_id("selection-list-text-input").fill("naturesv057+5477453@gmail.com")
        page.get_by_label("naturesv057+5477453@gmail.com").click()

        flex_property = get_flex_property(page, '[aria-label="View attachment"]')
        
        # Delete created file
        delete_file(filename)

        #Step 3: Check if the issue is resolved
        assert flex_property == "1 1 0%", "EReceipt thumbnail is being cut off at the bottom."  # Assert if the flex property is "1 1 0%"
