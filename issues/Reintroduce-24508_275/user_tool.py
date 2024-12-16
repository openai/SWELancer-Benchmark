import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

from playwright.sync_api import sync_playwright, expect, Browser, Page
from playwright.sync_api._context_manager import PlaywrightContextManager

from utils.trace_cleaner import trace_cleaner

EXPENSIFY = 'https://dev.new.expensify.com:8082/' 
FIRST_NAME = "Milan"
LAST_NAME = "T"


# Utility to generate a random email
def generate_random_email() -> str:
    return f"testerbro7077+8908spt@gmail.com"


# login a user in NewDot
def login_user(p: PlaywrightContextManager, first_name=FIRST_NAME, last_name=LAST_NAME) -> tuple[Browser, Page, str]:
    # Launch chromium and open new page
    browser = p.chromium.launch(channel="chrome", headless=True, slow_mo=2100, args=[
            "--ignore-certificate-errors",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ])
    page = browser.new_page()

    # Start tracing
    page.context.tracing.start(title="trace", screenshots=True, snapshots=True)

    user_email = generate_random_email()

    # Step 1: Open expensify url
    page.goto(EXPENSIFY)

    # Step 2: Enter email and click continue
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()
    

    # Step 3: Click join button
    try: 
        page.locator('button[tabindex="0"]').click()
        
    except Exception:
        pass
    expect(page.locator("text=What do you want to do today?")).to_be_visible()
        
    # Step 4: Select 'Track and budget expenses' in onobarding page and click Continue
    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()
    

    # Step 5: Enter first name, last name and click continue
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()
    

    return browser, page, user_email


# navigate to profile under settings
def navigate_to_profile(page: Page):  
    page.locator('button[aria-label="My settings"]').click()
    page.locator('div[aria-label="Profile"]').first.click()


# edit legal name
def edit_legal_name(page: Page):
    # click on legal name under profile
    page.locator('div[role="menuitem"]', has_text="Legal name").click()

    fname_input_field = page.locator('div[aria-label="Legal first name"] input')
    lname_input_field = page.locator('div[aria-label="Legal last name"] input')
    save_button = page.get_by_role('button', name="Save")

    fname_input_field.fill(FIRST_NAME + '÷')
    error_msg_fname = page.get_by_text("Name can only include Latin characters.")
    error_msg_lname = page.get_by_text("This field is required.")
    save_button.click()
    expect(error_msg_fname).to_be_visible()
    expect(error_msg_lname).to_be_visible()
    fname_input_field.clear()

    lname_input_field.fill(LAST_NAME + '×')
    error_msg_fname = page.get_by_text("This field is required.")
    error_msg_lname = page.get_by_text("Name can only include Latin characters.")
    save_button.click()
    expect(error_msg_fname).to_be_visible()
    expect(error_msg_lname).to_be_visible()
    lname_input_field.clear()

    fname_input_field.fill(FIRST_NAME + '×')
    lname_input_field.fill(LAST_NAME + '÷')
    save_button.click()
    error_msg = page.get_by_text("Name can only include Latin characters.").all()
    assert len(error_msg) == 2
    fname_input_field.clear()
    lname_input_field.clear()

    fname_input_field.fill(FIRST_NAME + '1234,@8.')
    error_msg_fname = page.get_by_text("Name can only include Latin characters.")
    error_msg_lname = page.get_by_text("This field is required.")
    save_button.click()
    expect(error_msg_fname).to_be_visible()
    expect(error_msg_lname).to_be_visible()
    fname_input_field.clear()

    lname_input_field.fill(LAST_NAME + '45945%^&')
    error_msg_fname = page.get_by_text("This field is required.")
    error_msg_lname = page.get_by_text("Name can only include Latin characters.")
    save_button.click()
    expect(error_msg_fname).to_be_visible()
    expect(error_msg_lname).to_be_visible()
    lname_input_field.clear()

    fname_input_field.fill(FIRST_NAME + '00765#)(1><')
    lname_input_field.fill(LAST_NAME + '4&~`;|8')
    save_button.click()
    error_msg = page.get_by_text("Name can only include Latin characters.").all()
    assert len(error_msg) == 2
    fname_input_field.clear()
    lname_input_field.clear()

    error_msg = page.get_by_text("This field is required.").all()
    assert len(error_msg) == 2

    

def test_fake_assignee_name_removed():
    with sync_playwright() as p:
        browser = None
        page = None
        try:
            browser, page, email = login_user(p)
            navigate_to_profile(page)
            edit_legal_name(page)
        except Exception as e:
            print("Test failed:", e)
            raise
        finally:
            if page:
                page.context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
                trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            if browser:
                browser.close()
