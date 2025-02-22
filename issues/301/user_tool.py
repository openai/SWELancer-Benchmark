import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
import pytest
from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page
from utils.trace_cleaner import trace_cleaner



def generate_random_email() -> str:
    timestamp = int(time.time())

    return "t56826807+1733398137@gmail.com"



def login_user(
    playwright: PlaywrightContextManager, first_name: str, last_name: str
) -> tuple[Browser, Page, str]:
    browser = playwright.chromium.launch(
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
    context = browser.new_context(
        viewport={"width": 360, "height": 640},
        user_agent="Mozilla/5.0 (Linux; Android 10; Mobile; rv:68.0) Gecko/68.0 Firefox/68.0",
    )
    page = context.new_page()
    user_email = generate_random_email()

    page.goto("https://dev.new.expensify.com:8082/")
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(1000)

    try:
        page.locator('button[tabindex="0"]').click()
        page.wait_for_timeout(1000)
    except Exception:
        pass

    expect(page.locator("text=What do you want to do today?")).to_be_visible()
    page.wait_for_timeout(1000)

    page.locator("text='Manage my team's expenses'").click()
    page.get_by_role("button", name="Continue").click()
    time.sleep(1)

    return browser, page, user_email



def create_profile(page: Page, first_name: str, last_name: str) -> None:
    page.locator('input[name="fwork"]').fill("Turingg")
    page.get_by_role("button", name="Continue").last.click()
    time.sleep(1)

    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()
    page.wait_for_timeout(1000)



def check_you(page: Page) -> None:
    page.locator(
        'button[aria-label="Start chat (Floating action)"][tabindex="0"]'
    ).click()
    time.sleep(1)


    page.locator('div[aria-label="Start chat"][role="menuitem"]').click()
    time.sleep(1)

    you = page.locator('button[aria-label="Yagna Sai (you)"]')
    assert you.is_visible()


@pytest.mark.parametrize("first_name, last_name", [("Yagna", "Sai")])
def test_run(first_name: str, last_name: str) -> None:
    with sync_playwright() as playwright:
        browser, page, user_email = login_user(playwright, first_name, last_name)
        context = page.context

        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        error = None
        try:
            create_profile(page, first_name, last_name)
            check_you(page)
        except Exception as e:
            error = e
        finally:

            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")

            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            browser.close()
        if error:
            raise error


if __name__ == "__main__":
    pytest.main([__file__])