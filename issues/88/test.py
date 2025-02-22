from playwright.sync_api import sync_playwright, expect
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright._impl._browser import Browser
from playwright._impl._page import Page


# Utility to generate an email
def generate_email():
    timestamp =  '500005'
    return f"freelanceapptest+{timestamp}@gmail.com"


# Function to log in the user and complete onboarding steps
def login_user(p: PlaywrightContextManager, first_name="Milan", last_name="T") -> tuple[Browser, Page, str]:
    # Launch Chromium and open a new page
    browser = p.chromium.launch(
        channel="chrome",
        headless=False,
        args=[
            "--ignore-certificate-errors",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ],
        proxy={"server": "http://localhost:8080"},
        slow_mo=200
    )

    context = browser.new_context(ignore_https_errors=True, viewport={"width": 1200, "height": 600})
    page = context.new_page()
    user_email = generate_email()

    # Step 1: Open the Expensify URL
    page.goto('https://dev.new.expensify.com:8082/') 

    # Step 2: Enter a generated email and click continue
    page.locator('input[type="email"]').fill(user_email)
    page.locator('button[tabindex="0"]').click()
    page.wait_for_timeout(1000) 

    # Step 3: Click the join button if available, otherwise skip
    try: 
        page.locator('button[tabindex="0"]').click() 
        page.wait_for_timeout(1000) 
    except Exception:
        pass

    # Step 4: Ensure that the user reaches the dashboard by checking for visible text
    expect(page.locator("text=What do you want to do today?")).to_be_visible()
        
    # Step 5: Select 'Track and budget expenses' in the onboarding page and click Continue
    page.locator("text='Track and budget expenses'").click()
    page.wait_for_timeout(1000) 

    # Step 6: Enter first name, last name, and continue
    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()
    page.wait_for_timeout(1000) 

    return browser, page


def create_expense(page, currency, amount):
    """Helper function to create an expense with the given currency and amount."""
    page.get_by_label("Create").click()
    track_expense_button = page.get_by_text("Track expense").nth(0)
    if track_expense_button.is_visible():
        track_expense_button.click()
    else:
        page.get_by_text("Create expense").click()
    page.get_by_label("Manual").click()
    page.get_by_label("Select a currency").click()
    page.get_by_test_id("selection-list-text-input").fill(currency.lower())
    page.get_by_label(f"{currency.upper()} - {get_currency_symbol(currency)}").click()
    page.get_by_placeholder("0").fill(str(amount))
    page.locator("#numPadContainerView").get_by_role("button", name="Next").click()
    page.get_by_role("button", name="Track expense").click()
    page.wait_for_timeout(1000)


def get_currency_symbol(currency):
    """Returns the correct currency symbol for a given currency code."""
    currency_map = {
        "usd": "$",
        "cad": "C$",
        "gbp": "£",
        "jpy": "¥"
    }
    return currency_map.get(currency.lower(), "?")


def test_lhn_scrollable():
    with sync_playwright() as p:
        # Step 1: Login user 
        browser, page = login_user(p)
        page.locator('span:has-text("Milan T (you)")').click()
        
        # Step 2: Create multiple tracked expenses
        create_expense(page, "usd", 10)
    
        # Step 3: Navigate to Search
        page.get_by_test_id("CustomBottomTabNavigator").get_by_label("Search").click()

        # Step 4: Apply filters and save searches
        # Each filter is applied differently based on its type
        page.get_by_role("button", name="Filters").click()

        # Filter by Currency (USD)
        page.get_by_text("Currency").click()
        page.get_by_test_id("selection-list-text-input").fill("usd")
        page.locator("[id=\"USD\\ -\\ \\$\"]").click()
        page.get_by_role("button", name="Save").click()
        page.get_by_role("button", name="Save search").click()
        page.wait_for_timeout(1000)
       
        # Filter by Expense Type (Cash)
        page.get_by_role("button", name="Filters").click()
        page.get_by_role("link", name="Reset filters").click()
        page.get_by_text("Expense type").click()
        page.locator("#Cash").click()
        page.get_by_role("button", name="Save").click()
        page.get_by_role("button", name="Save search").click()
        page.wait_for_timeout(1000)
        
        # Filter by Total Amount (Between 10 and 1000)
        page.get_by_role("button", name="Filters").click()
        page.get_by_role("link", name="Reset filters").click()
        page.get_by_test_id("SearchAdvancedFiltersPage").get_by_text("Total").click()
        page.get_by_role("textbox", name="Greater than").fill("10")
        page.get_by_role("textbox", name="Less than").click()
        page.get_by_role("textbox", name="Less than").fill("1000")
        page.get_by_role("button", name="Save").click()
        page.get_by_role("button", name="Save search").click()
        page.wait_for_timeout(1000)

        # Filter by Currency (AED)       
        page.get_by_role("button", name="Filters").click()
        page.get_by_role("link", name="Reset filters").click()
        page.get_by_test_id("SearchAdvancedFiltersPage").get_by_text("Currency").click()
        page.locator("[id=\"AED\\ -\\ Dhs\"]").get_by_label("AED - Dhs").click()
        page.get_by_role("button", name="Save").click()
        page.get_by_role("button", name="Save search").click()
        page.wait_for_timeout(1000)
        
        # Filter by Currency (JPY)
        page.get_by_role("button", name="Filters").click()
        page.get_by_role("link", name="Reset filters").click()
        page.get_by_test_id("SearchAdvancedFiltersPage").get_by_text("Currency").click()
        page.get_by_test_id("selection-list-text-input").fill("j")
        page.locator("[id=\"JPY\\ -\\ ¥\"]").click()
        page.get_by_role("button", name="Save").click()
        page.get_by_role("button", name="Save search").click()
        page.wait_for_timeout(1000)
        
        # Filter by Currency (AOA)
        page.get_by_role("button", name="Filters").click()
        page.get_by_role("link", name="Reset filters").click()
        page.get_by_test_id("SearchAdvancedFiltersPage").get_by_text("Currency").click()
        page.locator("button").filter(has_text="AOA - Kz").click()
        page.get_by_role("button", name="Save").click()
        page.get_by_role("button", name="Save search").click()
        page.wait_for_timeout(1000)
        
        # Filter by Currency (AUD)
        page.get_by_role("button", name="Filters").click()
        page.get_by_test_id("SearchAdvancedFiltersPage").get_by_text("AOA").click()
        page.locator("button").filter(has_text="AUD - A$").click()
        page.locator("button").filter(has_text="AOA - Kz").get_by_label("AOA - Kz").click()
        page.get_by_role("button", name="Save").click()
        page.get_by_role("button", name="Save search").click()
        page.wait_for_timeout(1000)

        # Filter by Currency (ALL)
        page.get_by_role("button", name="Filters").click()
        page.get_by_role("link", name="Reset filters").click()
        page.get_by_test_id("SearchAdvancedFiltersPage").get_by_text("Currency").click()
        page.locator("[id=\"ALL\\ -\\ ALL\"]").click()
        page.get_by_role("button", name="Save").click()
        page.get_by_role("button", name="Save search").click()

        # Step 5: Click "Expenses" in the bottom tab
        expenses_tab = page.get_by_test_id("SearchPageBottomTab").get_by_text("Expenses")
        expenses_tab.click()
        page.wait_for_timeout(1000)  # Allow UI to stabilize

        page.set_viewport_size({"width": 1200, "height": 500})

        # Step 6: Scroll the LHN to the bottom 
        aud_saved_search = page.get_by_text("type:expense status:all currency:AUD")
        aud_saved_search.hover()
        page.mouse.wheel(0, 600)     
        page.wait_for_timeout(1000)
    
        # Step 7: Verify the "Expenses" tab is not visible after scrolling
        locator = page.get_by_test_id("SearchPageBottomTab").get_by_text("Expenses")
        expect(locator).to_be_visible()

        # Get bounding box of the "Expenses" element
        bounding_box = locator.bounding_box()
       
        # Get current scroll position
        scroll_y = page.evaluate("window.scrollY")

        # Assert that the Expenses tab is not within the viewport
        assert not bounding_box["y"] >= scroll_y, f"Expense tab should not be inside the viewport but is at {bounding_box['y']} while scrollY is {scroll_y}"
        
        page.wait_for_timeout(2000)
        
        # Close browser
        browser.close()
