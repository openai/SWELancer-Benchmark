from playwright.sync_api import sync_playwright, expect


user_email = "openaipg+123@gmail.com"
password = "uufz cmac tzpo zihv"
firstname = "Prashant"
lastname = "Gupta"


def get_magic_code(page, user_email, password, since=None, retries=5, delay=10):
    # Return any value while replaying
    return "123456"


def login_with_magic_code(page):
    page.goto("https://dev.new.expensify.com:8082/")
    page.get_by_test_id("username").click()
    page.get_by_test_id("username").fill(user_email)
    page.get_by_role("button", name="Continue").click()
    page.get_by_test_id("validateCode").fill(
        get_magic_code(page, user_email, password))
    page.wait_for_timeout(2000)
    # for handling the initial popup, in case it appears
    try:
        page.get_by_text("Track and budget expenses").click()
        page.get_by_role("textbox", name="First name").fill(firstname)
        page.get_by_role("textbox", name="Last name").fill(lastname)

        page.get_by_role("button", name="Continue").click()
    except:
        pass


def test_member_details_in_room_chat():

    with sync_playwright() as p:

        # Launch chromium and open new page
        browser = p.chromium.launch(proxy={"server": "http://localhost:8080"}, headless=False, args=[
                                    "--no-sandbox", "--disable-dev-shm-usage", "--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"], slow_mo=1000, channel="chromium")
        context = browser.new_context()
        page = context.new_page()
        login_with_magic_code(page)
        page.wait_for_timeout(2000)

        try:
            page.locator(
                "#react-refresh-overlay").content_frame.get_by_role("button", name="× Close").click()
        except:
            pass

        page.get_by_label("My settings").click()
        page.get_by_test_id("InitialSettingsPage").get_by_label(
            "Workspaces").get_by_text("Workspaces").click()
        page.get_by_label("New workspace").click()

        page.get_by_label("Back").click()
        page.get_by_label("Start chat (Floating action)").click()
        page.get_by_text("Start chat").click()
        page.get_by_label("Room", exact=True).click()
        page.get_by_placeholder("social").fill(
            f"""teams721""")
        page.get_by_role("button", name="Create room").click()
        page.locator("#composer").fill("@+919789945670")
        page.get_by_label("Send").click()
        page.get_by_role("button", name="Invite them").click()
        page.get_by_label("#teams").click()
        page.get_by_text("Members").click()
        page.get_by_text("97899 45670").nth(2).click()
        expect(page.get_by_text("+919789945670@expensify.sms").nth(1)
               ).not_to_be_visible()

        # ---------------------
        context.close()
        browser.close()
