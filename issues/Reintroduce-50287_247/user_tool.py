import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright
from PIL import Image
from io import BytesIO
import pytest

# Import our trace cleaner
from utils.trace_cleaner import trace_cleaner

# Expensify app URL
NEWDOT_URL = "https://dev.new.expensify.com:8082/"
OLDDOT_URL = "http://localhost:9000/"
EMAIL = "f2139887+50287@gmail.com"
PASSWORD = "sdib pdop ovyl uawy"


def new_dot_login(page, email):
    page.goto(NEWDOT_URL)
    page.locator('input[type="email"]').fill(email)
    page.wait_for_timeout(2000)
    page.locator("div:nth-child(3) > div:nth-child(2) > div > div").first.click()
    # Wait for OTP
    page.wait_for_timeout(5000)
    otp = "123456"
    page.locator('input[name="validateCode"]').first.fill(otp)  # Focus
    page.get_by_text("Concierge").last.wait_for()


def create_sample_jpg():
    # Generates an image in memory and returns the bytes
    image = Image.new("RGB", (100, 100), color="blue")
    img_byte_arr = BytesIO()
    image.save(img_byte_arr, format="JPEG")
    img_byte_arr.seek(0)
    return img_byte_arr.getvalue()


def run_test(page, email_address):
    # change language to spanish
    rand_num = 26406
    page.get_by_label("My settings").click()
    page.get_by_text("Preferences").click()
    page.get_by_text("Language").click()
    page.get_by_label("Spanish").click()
    page.get_by_label("Recibidos").click()

    page.get_by_label("Iniciar chat (Acción flotante)").click()
    page.get_by_text("Iniciar chat").click()
    page.get_by_test_id("selection-list-text-input").click()
    page.get_by_test_id("selection-list-text-input").fill(
        f"f2139887+{rand_num}@gmail.com"
    )
    page.get_by_label(f"f2139887+{rand_num}@gmail.com").click()
    page.get_by_label("Crear").last.click()
    page.get_by_text("Presentar gasto").click()

    with page.expect_file_chooser() as fc_info:
        page.get_by_label("Elegir archivo").click()
        file_chooser = fc_info.value
        file_chooser.set_files(
            {
                "name": "input.jpg",
                "mimeType": "image/jpeg",
                "buffer": create_sample_jpg(),
            }
        )

    page.get_by_role("button", name="Presentar gasto").click()
    page.get_by_label("Ver detalles").last.click()
    page.get_by_text("Importe • Efectivo").click()
    page.get_by_placeholder("0").fill("100")
    page.get_by_role("button", name="Guardar").click()
    if page.get_by_text("estableció el importe").last.is_visible():
        print("Test Passed")
    else:
        print("Test Failed")
        pytest.fail(f"AssertionError: Test Failed")


def test_expensify_50287():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="chrome",
            headless=True,
            args=[
                "--ignore-certificate-errors",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
            ],
            proxy={"server": "http://localhost:8080"},
            slow_mo=500,
        )
        context_args = {}
        context_args["timezone_id"] = "Asia/Karachi"
        context_args["geolocation"] = {"latitude": 37.7749, "longitude": 122.4194}
        context_args["permissions"] = ["geolocation"]
        context_args["ignore_https_errors"] = True

        first_user_context = browser.new_context(**context_args)

        # Start tracing
        first_user_context.tracing.start(
            title="trace",
            path="/app/expensify/user_tool/output_browser1.zip",
            screenshots=True,
            snapshots=True,
            sources=True
        )

        try:
            first_user_page = first_user_context.new_page()
            new_dot_login(first_user_page, EMAIL)
            run_test(first_user_page, EMAIL)
        except Exception as e:
            print(f"Test ended with an error: {e}")
            raise
        finally:
            # Stop the trace and clean it
            first_user_context.tracing.stop()
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            first_user_context.close()
            browser.close()
