import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from utils.trace_cleaner import trace_cleaner

NEWDOT_URL = "https://dev.new.expensify.com:8082/"
EMAIL = "caraxxes555+456082@gmail.com"
PASSWORD = 'wawm wmyw omkr dpmt'


def choose_link_if_any(page, link_text, retries = 3):
    for _ in range(retries):
        link = page.locator(f'text={link_text}')
        if link.count() == 0:
            page.wait_for_timeout(1000)
        else:
            break

    if link.count() == 0:
        return 

    link.click()


def new_dot_login(page, email):
    page.goto(NEWDOT_URL)  
    page.locator('input[type="email"]').fill(email)
    
    page.get_by_role("button", name="Continue").nth(0).click()
    
    otp = "123456"
    page.locator('input[data-testid="validateCode"]').fill(otp)
    try:
        page.get_by_role("button", name="Sign In").click(timeout=1000)
    except:
        pass


def test_expensify_45608():
    with sync_playwright() as p:
        browser_1 = p.chromium.launch(headless=True, slow_mo=1000, args=["--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"])
        first_user_context = browser_1.new_context(ignore_https_errors=True)
        # Start tracing for first context
        first_user_context.tracing.start(screenshots=True, snapshots=True)
        page_1 = first_user_context.new_page()

        browser_2 = p.chromium.launch(headless=True, slow_mo=1000, args=["--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"])
        second_user_context = browser_2.new_context(ignore_https_errors=True)
        # Start tracing for second context
        second_user_context.tracing.start(screenshots=True, snapshots=True)
        page_2 = second_user_context.new_page()

        try:
            # Test steps
            new_dot_login(page_1, EMAIL)

            page_2.goto(NEWDOT_URL)
            new_dot_login(page_2, EMAIL)
            page_2.get_by_label("My settings").click()
            page_2.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()
            page_2.get_by_label("New workspace").first.click()
            choose_link_if_any(page_2, "Got it")
            page_2.get_by_label("Back").click()
            page_2.get_by_label("Preferences").click()
            page_2.get_by_role("menuitem", name="English").click()
            page_2.get_by_label("Spanish").click()
            page_1.wait_for_timeout(15000)
            expect(page_1.locator("span", has_text=" (tú)").first).to_be_visible()
            expect(page_1.locator("[aria-label*='Vista previa del último mensaje']", has_text="Este es tu espacio personal. Úsalo para notas, tareas, borradores y recordatorios.").first).to_be_visible()
            expect(page_1.locator("[aria-label*='Vista previa del último mensaje']", has_text="¡La colaboración entre ").first).to_be_visible()
        except Exception as e:
            # Reraise so the test framework sees the failure
            raise e
        finally:
            # Stop and export first context trace, then clean
            first_user_context.tracing.stop()
            first_user_context.tracing.export(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")

            # Stop and export second context trace, then clean
            second_user_context.tracing.stop()
            second_user_context.tracing.export(path="/app/expensify/user_tool/output_browser2.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser2.zip")

            browser_1.close()
            browser_2.close()
