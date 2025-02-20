from playwright.sync_api import sync_playwright
from utils.trace_cleaner import trace_cleaner

user_email = "testuserexpensify1@gmail.com"
password = "aedyeaocujbrrcal"
user_id = "testuserexpensify1+153@gmail.com"
didUIBlink = False


def login(p, if_phone=False, first_name="John", last_name="Doe"):
    # step 1: Login
    permissions = ['clipboard-read']
    browser = p.chromium.launch(headless=False, slow_mo=500, args=["--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"])

    if if_phone:
        phone = p.devices['iPhone 12 Pro']
        context = browser.new_context(**phone, permissions=permissions, reduced_motion='no-preference')
    else:
        context = browser.new_context()

    page = context.new_page()

    page.goto('https://dev.new.expensify.com:8082/') 

    phone_or_email_input = page.locator('input[type="email"]')
    phone_or_email_input.fill(user_id)

    continue_button = page.locator('button[tabindex="0"]')
    continue_button.click()
    magic_code = "123456"

    validate_code_input = page.locator('input[name="validateCode"]')
    validate_code_input.fill(magic_code)

    return browser, page


def test_51128():
    with sync_playwright() as p:
        browser, page = login(p, False)
        context = page.context
        # Start tracing with screenshots, snapshots and sources
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        try:
            chat_name = "testuser somasundar"
            amount = "1"
            try:
                page.get_by_text("Got it").click(timeout=2000)
            except:
                pass

            # Navigate to the chat
            page.get_by_label("Navigates to a chat").get_by_text(chat_name, exact=True).click()

            # Perform the first invoice action
            page.locator('button[aria-label="Create"]').click()
            page.locator('div[aria-label="Send invoice"][role="menuitem"]').click()
            page.locator('input[role="presentation"]').fill(amount)
            page.get_by_test_id("IOURequestStartPage").get_by_text("Next").click()
            page.get_by_test_id("IOURequestStepConfirmation").get_by_text("Send ₹").click()

            # Capture initial count of chat messages
            initialcount = page.get_by_test_id("report-actions-list").last.locator('div[aria-label="Chat message"]', has_text="Today at").count()
            print(f"Initial message count: {initialcount}")
            try:
                page.get_by_text("Got it").click(timeout=2000)
            except:
                pass

            # Perform the second invoice action
            page.locator('button[aria-label="Create"]').click()
            page.locator('div[aria-label="Send invoice"][role="menuitem"]').click()
            page.locator('input[role="presentation"]').fill(amount)
            page.get_by_test_id("IOURequestStartPage").get_by_text("Next").click()

            noBlinks = page.evaluate("""
                (() => {
                    return new Promise((resolve) => {
                        let reportActionsLists = document.querySelectorAll('[data-testid="report-actions-list"]');
                        if (reportActionsLists.length === 0) resolve(false); // Fail-safe if no elements found

                        let lastReportActionsList = reportActionsLists[reportActionsLists.length - 1];

                        // Function to count messages that contain "Today at"
                        const getMessageCount = () => {
                            let messages = lastReportActionsList.querySelectorAll('div[aria-label="Chat message"]');
                            return Array.from(messages).filter(msg => msg.innerText.includes("Today at")).length;
                        };

                        let countBefore = getMessageCount(); // Get initial count
                        let noBlinks = true;
                        
                        // Check message count every 10ms
                        let checkInterval = setInterval(() => {
                            let countDuring = getMessageCount();
                            if (countDuring !== countBefore) {
                                noBlinks = false;
                            }
                        }, 10);
                        
                        setTimeout(() => {
                            clearInterval(checkInterval); // Stop interval after 3 seconds and return final count
                            resolve(noBlinks); // Return state of noBlinks variable
                        }, 3000);
                        
                        let container = document.querySelector('[data-testid="IOURequestStepConfirmation"]');
                        if (!container) return;

                        let button = Array.from(container.querySelectorAll('button'))
                                        .find(btn => btn.innerText.includes("Send ₹"));

                        if (button) {
                            button.click();
                        } else {
                            noBlinks = false; //If no button found, test should fail
                        }
                    });
                })();
            """)
            assert noBlinks, "The invoice preview sender appears then disappears when sending invoices consecutively."
        finally:
            # Stop tracing, export the trace file, run trace cleaner, and close the browser
            trace_file = "/app/expensify/user_tool/output_browser1.zip"
            context.tracing.stop(path=trace_file)
            trace_cleaner(trace_file)
            browser.close()


if __name__ == "__main__":
    test_51128()
