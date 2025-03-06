import logging
import sys
from playwright.sync_api import sync_playwright
from playwright._impl._browser import Browser
from playwright._impl._page import Page
from playwright.sync_api._context_manager import PlaywrightContextManager
from bs4 import BeautifulSoup

# Expensify app URL
NEWDOT_URL = "https://dev.new.expensify.com:8082"
OLDDOT_URL = "http://127.0.0.1:9000/"

# Logger
logging.basicConfig(level=logging.INFO, stream=sys.stdout, format="%(message)s")
LOGGER = logging.getLogger(__name__)

def login_user(p: PlaywrightContextManager, first_name="Milan", last_name="T") -> tuple[Browser, Page, str]:

    # Launch chromiun and open new page
    browser = p.chromium.launch(headless=False, args=[
        "--ignore-certificate-errors",
        "--disable-web-security",
        "--disable-features=IsolateOrigins,site-per-process"
    ], proxy = {"server": "http://127.0.0.1:8080/"}, slow_mo=1000)
    context = browser.new_context()
    page = context.new_page()

    # Step 1: Open expensify url
    page.goto('https://dev.new.expensify.com:8082/') 

    # Step 2: Enter email and click continue
    page.locator('input[type="email"]').fill("rgarciatammy4+17396175336468@gmail.com")
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(1000)

    # Step 3: Click join button
    page.get_by_role("button", name="Join").click()
        
    # Step 4: Select 'Track and budget expenses' in onobarding page and click Continue
    page.locator("text='Track and budget expenses'").click()
    page.get_by_role("button", name="Continue").click()
    page.wait_for_timeout(1000)

    # Step 5: Enter first name, last name and click continue
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()
    page.wait_for_timeout(1000)

    return browser, page

def normalize_svg(svg_str):
    # Parses and normalizes an SVG string to remove formatting differences.
    return str(BeautifulSoup(svg_str, "html.parser"))

def test_update_icons_issue():
    with sync_playwright() as pw:
        browser, page = login_user(pw)

        # SVG's to be used for comparison
        document_slash_svg = '''<path d="M18 13.986V7.5a.5.5 0 0 0-.5-.5h-6a.5.5 0 0 1-.5-.5v-6a.5.5 0 0 0-.5-.5H4c-.47 0-.904.163-1.245.435L18 13.986ZM2 7.792V18a2 2 0 0 0 2 2h11.734L2 7.792Z"></path><path d="m13 0 5 5h-4.5a.5.5 0 0 1-.5-.5V0ZM1.664 2.253A1 1 0 1 0 .336 3.747l18 16a1 1 0 0 0 1.328-1.494l-18-16Z"></path>'''
        file_image_svg = '''<path d="M14.1.4 18.7 5c.7.7.2 2-.9 2h-4.6c-.7 0-1.2-.5-1.2-1.2V1.2c0-1.1 1.3-1.6 2.1-.8z"></path><path d="M2.5 0C1.7 0 1 .7 1 1.5v17c0 .8.7 1.5 1.5 1.5h15c.8 0 1.5-.7 1.5-1.5v-7.9c0-.9-.7-1.6-1.5-1.6h-6c-.8 0-1.5-.6-1.5-1.5v-6C10 .7 9.3 0 8.5 0h-6z"></path>'''
        close_svg ='''<path d="M14.6 17.4c.8.8 2 .8 2.8 0 .8-.8.8-2 0-2.8L12.8 10l4.6-4.6c.8-.8.8-2 0-2.8-.8-.8-2-.8-2.8 0L10 7.2 5.4 2.6c-.8-.8-2-.8-2.8 0s-.8 2 0 2.8L7.2 10l-4.6 4.6c-.8.8-.8 2 0 2.8.8.8 2 .8 2.8 0l4.6-4.6 4.6 4.6z"></path>'''
        tick_svg = '''<path d="M17.2 3.4c.9.7 1.1 1.9.4 2.8L8.9 18l-6.3-5.7c-.8-.7-.9-2-.1-2.8.7-.8 2-.9 2.8-.1l3 2.7 6.1-8.2c.6-1 1.9-1.2 2.8-.5z" style="fill-rule: evenodd; clip-rule: evenodd;"></path>'''

        page.get_by_label("Start chat (Floating action)").click()
        page.get_by_label("New workspace").click()
        page.get_by_label("Categories").click()
        page.locator("#Advertising").get_by_label("Advertising").click()
        page.locator("#Benefits").get_by_label("Benefits").click()
        page.get_by_role("button", name="selected").click()
        disable_categories_image = page.get_by_label("Disable categories").get_by_role("img")
        disable_image_inner_html = disable_categories_image.inner_html()
        normalized_disable_image_inner_html = normalize_svg(disable_image_inner_html)
        normalized_document_slash_svg = normalize_svg(document_slash_svg)
        normalized_close_svg = normalize_svg(close_svg)
        page.get_by_label("Disable categories").click()
        page.locator("#Advertising").get_by_label("Advertising").click()
        page.locator("#Benefits").get_by_label("Benefits").click()
        page.get_by_role("button", name="selected").click()
        enable_image = page.get_by_label("Enable categories").get_by_role("img")
        enable_image_inner_html = enable_image.inner_html()
        normalized_enable_image_inner_html = normalize_svg(enable_image_inner_html)
        normalized_file_image_svg = normalize_svg(file_image_svg)
        normalized_tick_svg = normalize_svg(tick_svg)
        page.get_by_label("Enable categories").click()

        # Comparing the SVGs
        assert normalized_disable_image_inner_html != normalized_document_slash_svg, "Document slash icon should be updated to close icon!"
        assert normalized_enable_image_inner_html != normalized_file_image_svg, "File icon should be updated to tick icon!"
        assert normalized_disable_image_inner_html == normalized_close_svg, "Close icon should be present!"
        assert normalized_enable_image_inner_html == normalized_tick_svg, "Tick icon should be present1"

        # Close the browser
        page.close()
        browser.close()