import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import re
from playwright.sync_api import sync_playwright, expect
from email.header import decode_header
from utils.trace_cleaner import trace_cleaner


def login_user(p) -> tuple:
    user_email = "testerbro7077@gmail.com"
    password = "xqxz mmcb tvkn lpgp"
    
    browser = p.chromium.launch(headless=True, slow_mo=1000, args=[
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ])
    context = browser.new_context()
    page = context.new_page()

    page.goto('https://dev.new.expensify.com:8082/') 

    page.get_by_test_id("username").fill(user_email)
    page.get_by_role("button", name="Continue").click()
    page.wait_for_timeout(1000)
    

    magic_code = "123456"

    validate_code_input = page.locator('input[name="validateCode"]').nth(0)
    expect(validate_code_input).to_be_visible()
    validate_code_input.fill(magic_code)

    page.wait_for_timeout(1000)

    return browser, page, user_email


def test_save_description_in_submitted_expense():
    with sync_playwright() as p:
        browser, page, user_email = login_user(p)
        context = browser.contexts[0]

        # Start tracing
        context.tracing.start(
            title="trace for test_save_description_in_submitted_expense",
            screenshots=True,
            snapshots=True
        )

        try:
            page.get_by_label("My settings").click()
            page.get_by_text("Preferences").click()

            page.locator("div").filter(has_text=re.compile(r"^English$")).first.click()
            page.get_by_label("Spanish").click()
            page.get_by_label("Recibidos").click()
            page.get_by_label("Mi configuración").click()
            page.get_by_label("Espacios de trabajo").last.click()
            page.get_by_label("Nuevo espacio de trabajo").click()
            page.get_by_label("Volver").click()
            page.get_by_label("Recibidos").click()
            page.wait_for_timeout(2000)
            page.get_by_label("Crear").last.click()
            page.get_by_text("Presentar gasto").click()
            page.get_by_label("Manual").click()
            page.get_by_placeholder("0").fill("2300")
            page.locator("#numPadContainerView").get_by_role("button", name="Siguiente").click()
            page.get_by_text("Comerciante").click()
            page.get_by_role("textbox", name="Comerciante").fill("test")
            page.get_by_role("button", name="Guardar").click()
            page.locator('button div:has-text("Solicitar")').click()
            page.wait_for_timeout(2000)
            page.keyboard.press("Enter")
            page.get_by_label("Ver detalles").get_by_role("button").nth(1).click()
            page.get_by_text(re.compile(r"de otra forma$")).click()
            page.get_by_role("button", name=re.compile(r"de otra forma$")).click()
            assert page.get_by_text("Pago completo").is_visible()
            page.wait_for_timeout(3000)
        except Exception as e:
            # Re-raise after we stop tracing and clean it
            raise e
        finally:
            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            context.tracing.stop(path=trace_path)
            trace_cleaner(trace_path)
            browser.close()
