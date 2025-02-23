import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect
from utils.trace_cleaner import trace_cleaner



def generate_random_email():
    return f"testerbro7077+sg@gmail.com"



def login_user(page, user_email: str, first_name: str, last_name: str):

    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()

    try:
        page.locator('button[tabindex="0"]').click()
    except Exception:
        pass
    expect(page.locator("text=What do you want to do today?")).to_be_visible()

    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()



    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()


def test_expensify_24381():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True, slow_mo=700, args=[
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ])
        context = browser.new_context()

        context.tracing.start(snapshots=True, screenshots=True)

        page = context.new_page()
        try:
            page.goto('https://dev.new.expensify.com:8082/')
            login_user(page, generate_random_email(), "Test", "User")

            page.get_by_label("Start chat (Floating action)").click()
            page.get_by_label("New workspace").click()
            page.get_by_text("More features").click()

            workspace_link = page.url
            page.get_by_text("Profile").nth(1).click()
            page.get_by_label("Delete").click()
            page.get_by_role("dialog").get_by_role("button", name="Delete").click()

            page.goto(workspace_link)
            expect(page.get_by_role("link", name="Go back to home page")).to_be_visible()
        except Exception as e:
            raise e
        finally:

            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")

        context.close()
        browser.close()
