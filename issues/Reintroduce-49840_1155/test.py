import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect

static_email = "aquasaddam+52@gmail.com"

# Function to check message
def check_message(page):
    page.get_by_label("My settings").wait_for(state="visible")
    page.get_by_label("My settings").click()
    
    page.get_by_text("Preferences").wait_for(state="visible")
    page.get_by_text("Preferences").click()
    
    page.get_by_label("English").wait_for(state="visible")
    page.get_by_label("English").click()
    
    page.get_by_label("Spanish").wait_for(state="visible")
    page.get_by_label("Spanish").click()
    
    page.get_by_label("Espacios de trabajo").wait_for(state="visible")
    page.get_by_label("Espacios de trabajo").click()
    
    page.get_by_label("Nuevo espacio de trabajo").first.wait_for(state="visible")
    page.get_by_label("Nuevo espacio de trabajo").first.click()

    page.get_by_label("INR - ₹").wait_for(state="visible")
    page.get_by_label("INR - ₹").click()
    
    page.get_by_test_id("selection-list-text-input").wait_for(state="visible")
    page.get_by_test_id("selection-list-text-input").fill("usd")
    
    page.get_by_label("USD - $").wait_for(state="visible")
    page.get_by_label("USD - $").click()
    
    page.get_by_role("button", name="Volver").first.wait_for(state="visible")
    page.get_by_role("button", name="Volver").first.click()
    
    page.get_by_label("Recibidos").wait_for(state="visible")
    page.get_by_label("Recibidos").click()

    # Click on the button by locating the aria-label and specific text
    workspace_button = page.locator('//button[@aria-label="Navega a un chat" and .//div[contains(text(), "Test user\'s Workspace")]]')
    
    # Wait for the button to be visible and then click
    workspace_button.first.wait_for(state="visible")
    workspace_button.first.click()
    
    page.get_by_role("button", name="Crear").wait_for(state="visible")
    page.get_by_role("button", name="Crear").click()
    
    page.get_by_label("Presentar gasto").wait_for(state="visible")
    page.get_by_label("Presentar gasto").click()
    
    page.get_by_label("Manual").wait_for(state="visible")
    page.get_by_label("Manual").click()
    
    page.get_by_placeholder("0").wait_for(state="visible")
    page.get_by_placeholder("0").fill("1122")
    
    page.locator("#numPadContainerView").get_by_role("button", name="Siguiente").wait_for(state="visible")
    page.locator("#numPadContainerView").get_by_role("button", name="Siguiente").click()
    
    page.get_by_role("menuitem", name="Comerciante Obligatorio").wait_for(state="visible")
    page.get_by_role("menuitem", name="Comerciante Obligatorio").click()
    
    page.get_by_role("textbox", name="Comerciante").wait_for(state="visible")
    page.get_by_role("textbox", name="Comerciante").fill("test")
    
    page.get_by_role("button", name="Guardar").wait_for(state="visible")
    page.get_by_role("button", name="Guardar").click()
    
    page.get_by_role("button", name="Solicitar 1122,00 US$").wait_for(state="visible")
    page.get_by_role("button", name="Solicitar 1122,00 US$").click()
    
    page.get_by_label("Ver detalles").get_by_role("button").nth(1).wait_for(state="visible")
    page.get_by_label("Ver detalles").get_by_role("button").nth(1).click()
    
    page.get_by_label("Pagar 1122,00 US$ de otra").wait_for(state="visible")
    page.get_by_label("Pagar 1122,00 US$ de otra").click()
    
    page.get_by_role("button", name="Pagar 1122,00 US$ de otra").wait_for(state="visible")
    page.get_by_role("button", name="Pagar 1122,00 US$ de otra").click()
    
    # Check if "Pago completo" appears briefly within a timeout
    page.locator('button[aria-label="Ver detalles"]:has-text("Pago completo")').last.wait_for(state="visible", timeout=1500)



# Test execution function
def test_run():

    site_url = 'https://dev.new.expensify.com:8082/'

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, slow_mo=1000, args=["--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"])
        context = browser.new_context()
        page = context.new_page()

        page.goto(site_url) 

        phone_or_email_input = page.locator('input[type="email"]')
        phone_or_email_input.fill(static_email)

        continue_button = page.locator('button[tabindex="0"]')
        continue_button.click()

        try: 
            print("Maybe we need to click again")
            continue_button = page.locator('button[tabindex="0"]')

            continue_button.click()
        except Exception as e:
            pass
        

        # Click on Something else
        page.locator("text='Track and budget expenses'").wait_for()
        page.locator("text='Track and budget expenses'").click()
        page.get_by_role("button", name="Continue").click()

        # Enter first name and last name
        page.locator('input[name="fname"]').fill("Test")
        page.locator('input[name="lname"]').fill("user")
        page.get_by_role("button", name="Continue").last.click()
        page.get_by_label('Last chat message preview').filter(has_text='task for Track an expense').click()

        # Step 3: Verify that the back button is aligned properly on the not found page of workspace settings
        # Perform back actions
        check_message(page)
        page.wait_for_timeout(1000)
        # close the browser
        browser.close()