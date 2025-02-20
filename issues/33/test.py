import time
from playwright.sync_api import Page, sync_playwright


EXPENSIFY_URL = "https://dev.new.expensify.com:8082/"
FIRST_NAME = "Asaad"
LAST_NAME = "I"
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


def verify_search_LHN_items_height(page: Page):
    # Step 1: Open Search page
    page.get_by_test_id("CustomBottomTabNavigator").get_by_label("Search").click()

    # Step 2: Verify that the height of the LHN options in search is correct
    LHN_options = page.get_by_test_id("SearchPageBottomTab").get_by_role("menuitem")
    for i in range(LHN_options.count()):
        option = LHN_options.nth(i)
        assert (
            option.bounding_box()["height"] == 52
        ), f"Height of LHN items in search is not 52"


def verify_settings_LHN_items_height(page: Page):
    # Step 1: Open Settings page
    page.get_by_test_id("CustomBottomTabNavigator").get_by_label("Settings").click()

    # Step 2: Verify that the height of the LHN options in settings is correct
    LHN_options = page.get_by_test_id("InitialSettingsPage").get_by_role("menuitem")
    for i in range(LHN_options.count()):
        option = LHN_options.nth(i)
        assert (
            option.bounding_box()["height"] == 52
        ), f"Height of LHN items in settings is not 52"


def verify_workspace_LHN_items_height(page: Page):
    # Step 1: Open Workspace page
    page.get_by_test_id("CustomBottomTabNavigator").get_by_label(
        "Start chat (Floating action)"
    ).click()

    page.get_by_label("New workspace").click()

    # Step 2: Verify that the height of the LHN options in workspace is correct
    LHN_options = page.get_by_test_id("WorkspaceInitialPage").get_by_role("menuitem")
    for i in range(LHN_options.count()):
        option = LHN_options.nth(i)
        assert (
            option.bounding_box()["height"] == 52
        ), f"Height of LHN items in workspace is not 52"


def test_search_LHN_options_height():
    """
    This test verifies that the height of the LHN options is correct.
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

        # Step 2: Verify that the height of the LHN options in search is correct
        verify_search_LHN_items_height(page)

        # Step 3: Verify that the height of the LHN options in settings is correct
        verify_settings_LHN_items_height(page)

        # Step 4: Verify that the height of the LHN options in workspace is correct
        verify_workspace_LHN_items_height(page)

        # Step 5: Cleanup
        page.close()
        context.close()
        browser.close()
