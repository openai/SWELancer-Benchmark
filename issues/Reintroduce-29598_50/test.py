import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, Locator
from playwright._impl._page import Page
import os

# Utility to generate a random email
def generate_random_email():
    return f"testerbro7077+98789455@gmail.com".lower()


def login_user(page: Page, first_name="Milan", last_name="T"):
    # Launch chromiun and open ne   w page
    user_email = generate_random_email()

    # Step 1: Open expensify url
    page.goto('https://dev.new.expensify.com:8082/') 

    # Step 2: Enter email and click continue
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button', has_text="Continue").click()

    # Step 3: Click join button
    page.locator('button', has_text="Join").click()
    
    # Step 4: Select 'Track and budget expenses' in onobarding page and click Continue
    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()
    
    # Step 5: Enter first name, last name and click continue
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("form").get_by_role("button", name="Continue").click()
    page.get_by_text("Welcome to Expensify").wait_for()


def check_if_an_element_is_entirely_clickable(page: Page, element: Locator):
    """
    This function checks if an element is entirely clickable.
    """

    element.wait_for()

    # Get the dimensions of the element container
    element_box = element.bounding_box()

    # Create a grid of points to test clickability
    rows, cols = 3, 3
    for i in range(rows):
        for j in range(cols):
            x = element_box['x'] + (j + 0.5) * element_box['width'] / cols
            y = element_box['y'] + (i + 0.5) * element_box['height'] / rows

            # Move mouse to the point and check if it's clickable
            page.mouse.move(x, y)
            is_clickable = page.evaluate("""
                    ([x, y]) => {
                        const el = document.elementFromPoint(x, y);
                        return window.getComputedStyle(el).cursor === 'pointer';
                    }
                """, [x, y])
            if not is_clickable:
                return False
    return True


def check_if_close_button_is_entirely_clickable(page: Page, file_name: str):
    """
    This function checks if the attachment close button is entirely clickable.
    """

    # Step 1: Get the file path from the project root
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, file_name)

    # Step 2: Open your space chat page
    page.get_by_text("Asaad I (you)").wait_for()
    page.get_by_text("Asaad I (you)").click()

    # Step 3: Clik on + button
    page.get_by_test_id("report-actions-list").get_by_text("Your space").wait_for()
    page.get_by_label("Create").last.click()

    # Step 4: Intercept file chooser with expect_file_chooser
    with page.expect_file_chooser() as fc_info:
        # Step 5: Click the "Add attachment" button
        page.get_by_label("Add attachment").click()

    # Step 6: Handle the file chooser
    file_chooser = fc_info.value
    file_chooser.set_files(file_path)


    # Step 7: Wait for the close button to be visible
    close_button = page.get_by_label("Close")

    # Step 8: Check if the close button is entirely clickable
    is_clickable = check_if_an_element_is_entirely_clickable(page, close_button)
    assert is_clickable, f"The Close button is not entirely clickable"


def test_close_button_is_entirely_clickable():
    """
    Test to verify that the close button is entirely clickable
    """
    with sync_playwright() as p:

        browser = p.chromium.launch(channel="chrome", headless=True, slow_mo=2100, args=[
            "--ignore-certificate-errors",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ])
        context = browser.new_context()
        page = context.new_page()

        # Step 1: Login to expensify
        login_user(page, "Asaad", "I")

        # Step 2: Check if the close button is entirely clickable
        check_if_close_button_is_entirely_clickable(page, "profile.webp")

        # Step 3: Close browser
        browser.close()

