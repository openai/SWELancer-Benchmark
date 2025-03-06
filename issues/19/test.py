from playwright.sync_api import sync_playwright, expect
import random
GMAIL_NAME = "nomandevtur"
GMAIL_APP_PASSWORD = "tpye xlsj axyq nltq"


def get_test_user_info(seed = None, first_name = None, last_name = None):
    if first_name is None:
        first_name = GMAIL_NAME

    if last_name is None:
        last_name = ""

    email = f"{GMAIL_NAME}+{seed}@gmail.com" if seed is not None else f"{GMAIL_NAME}@gmail.com"
    
    return {"email": email, "password": GMAIL_APP_PASSWORD, "first_name": first_name, "last_name": last_name} 
    


def login_user(page, user_info, activity_text="Track and budget expenses"):
    # Clear cookies, local storage, and session storage
    page.context.clear_cookies()

    page.goto('https://dev.new.expensify.com:8082/', timeout=60000)
    page.wait_for_load_state('load', timeout=60000)
    

    page.get_by_test_id("username").fill(user_info["email"])
    page.get_by_role("button", name="Continue").click()

    page.wait_for_timeout(5000)
    join_button = page.get_by_role("button", name="Join")
    join_button.click(timeout=3000)
    
    page.wait_for_timeout(5000)

    # Select activity in onboarding page and click Continue
    page.get_by_label(activity_text).click()

    # Enter first name, last name and click continue
    page.get_by_role("textbox", name="First name").fill(user_info["first_name"])
    page.get_by_role("textbox", name="Last name").fill(user_info["last_name"])
    page.get_by_role("button", name="Continue").last.click()

def launch_app(pw, headless=False, device=None, geolocation=None):
    browser = pw.chromium.launch(
            proxy = {"server": "http://localhost:8080"}, 
            headless = False, 
            args = ["--no-sandbox", "--disable-dev-shm-usage", "--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"], 
            slow_mo = 1500
        )

    context_args = {"viewport": {"width": 1124, "height": 640}}
    if device:
        context_args.update(pw.devices[device])
    if geolocation:
        context_args["geolocation"] = geolocation
        context_args["permissions"] = ["geolocation"]
    context = browser.new_context(**context_args)
    page = context.new_page()
    return browser, context, page
    
def test_54775():
    with sync_playwright() as p:
        
        # seed = "54775." + str(random.randint(0, 2**32 - 1)) 
        seed = "54775.9328798723"
        user_info = get_test_user_info(seed = seed, first_name="T", last_name="T")

        browser, context, page = launch_app(p)
        login_user(page, user_info)

        page.wait_for_timeout(3000)
        
        # Locate the div containing "Create expenses"
        div_locator = page.locator("div:has-text('Create expenses')").first

        # Ensure the div is visible before checking styles
        div_locator.wait_for(state="visible", timeout=5000)

        # Get the background color of the div
        background_color = div_locator.evaluate("el => window.getComputedStyle(el).backgroundColor")

        # Locate the SVG icon inside the div
        icon_locator = div_locator.locator("svg")

        # Get the icon color (fill attribute)
        icon_color = icon_locator.evaluate("el => el.getAttribute('fill')")

        # Locate the text inside the div
        text_locator = div_locator.locator("span:has-text('Create expenses')")

        # Get the text color
        text_color = text_locator.evaluate("el => window.getComputedStyle(el).color")

        # Locate the small triangle div (tooltip arrow) directly inside div_locator
        triangle_div_locator = div_locator.locator("div[style*='border-top-color']")


        # Get the border widths of the triangle div
        border_left_width = triangle_div_locator.evaluate("el => window.getComputedStyle(el).getPropertyValue('border-left-width')")
        border_right_width = triangle_div_locator.evaluate("el => window.getComputedStyle(el).getPropertyValue('border-right-width')")
        border_top_width = triangle_div_locator.evaluate("el => window.getComputedStyle(el).getPropertyValue('border-top-width')")

        # Print values for debugging
        print("Extracted Background Color:", background_color)
        print("Extracted Icon Color:", icon_color)
        print("Extracted Text Color:", text_color)
        print("Extracted Border Left Width:", border_left_width)
        print("Extracted Border Right Width:", border_right_width)
        print("Extracted Border Top Width:", border_top_width)

        # Expected values
        expected_background = "rgb(8, 82, 57)"
        expected_icon_color = "#03D47C"
        expected_text_color = "rgb(231, 236, 233)"
        expected_border_width = "8px"

        # Assertions to ensure extracted values match expectations
        assert background_color == expected_background, f"Background color mismatch! Expected: {expected_background}, Got: {background_color}"
        assert icon_color == expected_icon_color, f"Icon color mismatch! Expected: {expected_icon_color}, Got: {icon_color}"
        assert text_color == expected_text_color, f"Text color mismatch! Expected: {expected_text_color}, Got: {text_color}"
        assert border_left_width == expected_border_width, f"Border Left Width mismatch! Expected: {expected_border_width}, Got: {border_left_width}"
        assert border_right_width == expected_border_width, f"Border Right Width mismatch! Expected: {expected_border_width}, Got: {border_right_width}"
        assert border_top_width == expected_border_width, f"Border Top Width mismatch! Expected: {expected_border_width}, Got: {border_top_width}"


        page.wait_for_timeout(3000)

        
        page.close()
        browser.close()
