import time
import pytest
from playwright.sync_api import sync_playwright, Page
from utils.trace_cleaner import trace_cleaner


def generate_random_email():
    # return f"t56826807+{int(time.time())}@gmail.com"
    return "t56826807+1739702555@gmail.com"


@pytest.fixture
def setup_playwright():
    playwright = sync_playwright().start()

    browser = playwright.chromium.launch(
        headless=False,
        args=[
            "--ignore-certificate-errors",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
        ],
        proxy={"server": "http://localhost:8080"},
        slow_mo=500,
    )
    context = browser.new_context()
    page = context.new_page()

    yield playwright, browser, page

    # Cleanup is handled in the test's finally block


def login_user(page: Page, email: str):
    page.goto("https://dev.new.expensify.com:8082/")
    page.locator('input[type="email"]').fill(email)
    page.locator("button", has_text="Continue").click()
    page.locator("button", has_text="Join").click()


def complete_onboarding(page: Page, first_name: str, last_name: str = ""):
    page.locator("text='Track and budget expenses'").click()
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()


def test(setup_playwright):
    playwright, browser, page = setup_playwright
    context = page.context
    context.tracing.start(screenshots=True, snapshots=True, sources=True)

    try:
        email_user, name_user = generate_random_email(), "User A"
        
        login_user(page, email_user)
        
        complete_onboarding(page, name_user)
        
        page.evaluate("""
            window.consoleErrors = [];
            
            (function() {
                const oldConsoleError = console.error;
                console.error = function(...args) {
                    window.consoleErrors.push("ConsoleError: " + args.map(String).join(" "));
                    oldConsoleError.apply(console, args);
                };
            })();
        
            window.onerror = function(message, source, lineno, colno, error) {
                let fullMessage = `UncaughtError: ${message} at ${source}:${lineno}:${colno}`;
                if (error && error.stack) {
                    fullMessage += `\nStack: ${error.stack}`;
                }
                window.consoleErrors.push(fullMessage);
            };
        """)
        
        page.locator('button[aria-label="Navigates to a chat"]', has_text="User A (you)").click()
        
        page.locator("#composer").fill("abc")
        page.get_by_role("paragraph").click()
        page.keyboard.press("ControlOrMeta+a")
        page.keyboard.press("ControlOrMeta+c")
        page.keyboard.press("ControlOrMeta+v")
        
        error_detected = page.evaluate("""
            window.consoleErrors.some(msg => msg.includes("IndexSizeError"))
        """)
        
        print("error_detected: ", error_detected)
        assert not error_detected
    finally:
        trace_path = "/app/expensify/user_tool/output_browser1.zip"
        context.tracing.stop(path=trace_path)
        trace_cleaner(trace_path)
        browser.close()
        playwright.stop()