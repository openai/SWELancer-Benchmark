import time
from playwright.sync_api import Page, sync_playwright, expect


EXPENSIFY_URL = "https://dev.new.expensify.com:8082/"
FIRST_NAME = "Asaad"
LAST_NAME = "I"
SELF_CHAT = f"{FIRST_NAME} {LAST_NAME} (you)"
SLOW_MO = 500
PROXY_SERVER = "http://localhost:8080"


def generate_random_email(username="expensify66", domain="gmail.com", seed=None):
    if seed is None:
        seed = int(time.time())
    return f"{username}+{seed}@{domain}"


def login(page: Page):
    # Step 1: Open expensify url
    page.goto(EXPENSIFY_URL)

    email = generate_random_email()

    # Step 2: Enter email and click continue
    page.get_by_test_id("username").fill(email)
    page.get_by_role("button", name="Continue").click()

    # Step 3: Click join button
    page.get_by_role("button", name="Join").click()

    # Step 4: Select 'Track and budget expenses' in onobarding page and click Continue
    page.get_by_text("Track and budget expenses").click()
    page.get_by_role("button", name="Continue").click()

    # Step 5: Enter first name, last name and click continue
    page.get_by_role("textbox", name="First name").fill(FIRST_NAME)
    page.get_by_role("textbox", name="Last name").fill(LAST_NAME)
    page.get_by_role("form").get_by_role("button", name="Continue").click()

    # Step 6: Get ahead of welcome to expensify by clicking get started
    try:
        page.get_by_role("button", name="Get started").last.click(timeout=3000)
    except:
        # ignore the error  and proceed
        pass


def test_search_tool_tip_visible():
    """
    This test verifies that the search tool tip is visible when hovering over the search icon.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            slow_mo=SLOW_MO,
            args=(
                [
                    "--ignore-certificate-errors",
                    "--disable-web-security",
                    "--disable-features=IsolateOrigins,site-per-process",
                ]
                if PROXY_SERVER
                else None
            ),
            proxy={"server": PROXY_SERVER} if PROXY_SERVER else None,
        )
        context = browser.new_context()
        page = context.new_page()

        # Step 1: Login to expensify
        login(page)

        # Step 2: Open self DM
        page.get_by_label("Navigates to a chat").get_by_text(
            SELF_CHAT, exact=True
        ).click()

        # Step 3: Hover over search icon
        page_id = page.url.rstrip("/").split("/")[-1]
        page.get_by_test_id(f"report-screen-{page_id}").get_by_label("Search").hover()

        # Step 4: Verify that the search tool tip is visible
        expect(
            page.locator("span", has_text="Search"), "Search tool tip is not visible"
        ).to_be_visible()

        # Step 5: Cleanup
        page.close()
        context.close()
        browser.close()
