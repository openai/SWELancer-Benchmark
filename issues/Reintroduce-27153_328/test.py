import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect

GMAIL_NAME = "testerbro7077"
GMAIL_APP_PASSWORD = "xqxz mmcb tvkn lpgp"

def get_test_user_info(seed=None, first_name=None, last_name=None):
    if first_name is None:
        first_name = "Yagan"

    if last_name is None:
        last_name = "Sai"

    email = f"{GMAIL_NAME}+{seed}@gmail.com" if seed is not None else f"{GMAIL_NAME}@gmail.com"
    return {"email": email, "password": GMAIL_APP_PASSWORD, "first_name": first_name, "last_name": last_name}


def login_user(page, user_info):
    page.goto('http://localhost:8082')
    page.wait_for_load_state('load')

    page.get_by_role("textbox", name="Phone or email").fill(user_info["email"])
    page.get_by_role("button", name="Continue").click()


    validate_code_input = page.locator("div:nth-child(2) > div > div > div > .css-view-175oi2r > .css-textinput-11aywtz").first
    expect(validate_code_input).to_be_visible()


    magic_code = "123456"
    print(f"Magic code: {magic_code}")
    validate_code_input.fill(magic_code)

    page.wait_for_timeout(3000)


def check_scroll(page):
    page.get_by_test_id("6978374583921682").click()
    page.get_by_role("button", name="Actions").click()
    page.get_by_role("textbox", name="Write something...").click()
    page.get_by_role("textbox", name="Write something...").fill("*Lorem Ipsum* is simply dummy text of the printing and typesetting industry. Lorem Ipsum has been the industry's standard dummy text ever since the 1500s, when an unknown printer took a galley of type and scrambled it to make a type specimen book. It has survived not only five centuries, but also the leap into electronic typesetting, remaining essentially unchanged. It was popularised in the 1960s with the release of Letraset sheets containing Lorem Ipsum passages, and more recently with desktop publishing software like Aldus PageMaker including versions of Lorem Ipsum.\n*Lorem Ipsum* is simply dummy text of the printing and typesetting industry. Lorem Ipsum has been the industry's standard dummy text ever since the 1500s, when an unknown printer took a galley of type and scrambled it to make a type specimen book. It has survived not only five centuries, but also the leap into electronic typesetting, remaining essentially unchanged. It was popularised in the 1960s with the release of Letraset sheets containing Lorem Ipsum passages, and more recently with desktop publishing software like Aldus PageMaker including versions of Lorem Ipsum.\n*Lorem Ipsum* is simply dummy text of the printing and typesetting industry. Lorem Ipsum has been the industry's standard dummy text ever since the 1500s, when an unknown printer took a galley of type and scrambled it to make a type specimen book. It has survived not only five centuries, but also the leap into electronic typesetting, remaining essentially unchanged. It was popularised in the 1960s with the release of Letraset sheets containing Lorem Ipsum passages, and more recently with desktop publishing software like Aldus PageMaker including versions of Lorem Ipsum.\n*Lorem Ipsum* is simply dummy text of the printing and typesetting industry. Lorem Ipsum has been the industry's standard dummy text ever since the 1500s, when an unknown printer took a galley of type and scrambled it to make a type specimen book. It has survived not only five centuries, but also the leap into electronic typesetting, remaining essentially unchanged. It was popularised in the 1960s with the release of Letraset sheets containing Lorem Ipsum passages, and more recently with desktop publishing software like Aldus PageMaker including versions of Lorem Ipsum.\n*Lorem Ipsum* is simply dummy text of the printing and typesetting industry. Lorem Ipsum has been the industry's standard dummy text ever since the 1500s, when an unknown printer took a galley of type and scrambled it to make a type specimen book. It has survived not only five centuries, but also the leap into electronic typesetting, remaining essentially unchanged. It was popularised in the 1960s with the release of Letraset sheets containing Lorem Ipsum passages, and more recently with desktop publishing software like Aldus PageMaker including versions of Lorem Ipsum.\n*Lorem Ipsum* is simply dummy text of the printing and typesetting industry. Lorem Ipsum has been the industry's standard dummy text ever since the 1500s, when an unknown printer took a galley of type and scrambled it to make a type specimen book. It has survived not only five centuries, but also the leap into electronic typesetting, remaining essentially unchanged. It was popularised in the 1960s with the release of Letraset sheets containing Lorem Ipsum passages, and more recently with desktop publishing software like Aldus PageMaker including versions of Lorem Ipsum.\n*Lorem Ipsum* is simply dummy text of the printing and typesetting industry. Lorem Ipsum has been the industry's standard dummy text ever since the 1500s, when an unknown printer took a galley of type and scrambled it to make a type specimen book. It has survived not only five centuries, but also the leap into electronic typesetting, remaining essentially unchanged. It was popularised in the 1960s with the release of Letraset sheets containing Lorem Ipsum passages, and more recently with desktop publishing software like Aldus PageMaker including versions of Lorem Ipsum.\n")
    page.wait_for_timeout(2000)
    page.reload()
    page.wait_for_timeout(1000)
    # Locate the textarea
    textarea = page.locator('textarea.css-textinput-11aywtz')

    # Evaluate if the scroll is at the bottom
    is_at_bottom = textarea.evaluate("""
        element => element.scrollTop + element.clientHeight >= element.scrollHeight
    """)

    # Assert that the scroll is at the bottom
    assert is_at_bottom, "App maintains focus but does not scroll to bottom at cursor position in compose box"



def test_login():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, slow_mo=500, args=[
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ])

        userA_info = get_test_user_info(seed=2, first_name="Yagna")
        contextA = browser.new_context()
        pageA = contextA.new_page()

        login_user(pageA, userA_info)
        check_scroll(pageA)


        pageA.close()
        contextA.close()
        browser.close()

